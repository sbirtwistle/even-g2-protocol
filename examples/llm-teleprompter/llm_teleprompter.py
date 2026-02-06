#!/usr/bin/env python3
"""
LLM Teleprompter - Query AI and Display on G2 Glasses

Queries an LLM provider and displays the Q&A on the Even AI card.
Supports multiple providers: OpenAI, Azure, Anthropic, Ollama.

Usage:
    python llm_teleprompter.py "What is the capital of France?"
    python llm_teleprompter.py "Explain quantum computing" --provider ollama
    python llm_teleprompter.py --interactive

Requirements:
    pip install -r requirements.txt
    cp .env.example .env  # Configure your API keys
"""

import asyncio
import argparse
import time
from bleak import BleakClient, BleakScanner

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from providers import get_provider, LLMProvider

# BLE UUIDs
UUID_BASE = "00002760-08c2-11e1-9073-0e8ac72e{:04x}"
CHAR_WRITE = UUID_BASE.format(0x5401)
CHAR_NOTIFY = UUID_BASE.format(0x5402)


# =============================================================================
# CRC & Encoding (from even_ai.py)
# =============================================================================

def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT for packet framing."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def encode_varint(value: int) -> bytes:
    """Encode integer as protobuf varint."""
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def build_packet(seq: int, svc_hi: int, svc_lo: int, payload: bytes) -> bytes:
    """Build G2 packet with header and CRC."""
    header = bytes([0xAA, 0x21, seq, len(payload) + 2, 0x01, 0x01, svc_hi, svc_lo])
    full = header + payload
    crc = crc16_ccitt(payload)
    return full + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


# =============================================================================
# Authentication (from even_ai.py)
# =============================================================================

def build_auth_packets() -> list:
    """Build 7-packet authentication sequence."""
    timestamp = int(time.time())
    ts_varint = encode_varint(timestamp)
    txid = bytes([0xE8, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x01])

    packets = []

    # Auth 1-2: Capability exchange
    p1 = bytes([0xAA, 0x21, 0x01, 0x0C, 0x01, 0x01, 0x80, 0x00,
                0x08, 0x04, 0x10, 0x0C, 0x1A, 0x04, 0x08, 0x01, 0x10, 0x04])
    packets.append(p1 + bytes([crc16_ccitt(p1[8:]) & 0xFF, (crc16_ccitt(p1[8:]) >> 8) & 0xFF]))

    p2 = bytes([0xAA, 0x21, 0x02, 0x0A, 0x01, 0x01, 0x80, 0x20,
                0x08, 0x05, 0x10, 0x0E, 0x22, 0x02, 0x08, 0x02])
    packets.append(p2 + bytes([crc16_ccitt(p2[8:]) & 0xFF, (crc16_ccitt(p2[8:]) >> 8) & 0xFF]))

    # Auth 3: Time sync
    payload3 = bytes([0x08, 0x80, 0x01, 0x10, 0x0F, 0x82, 0x08, 0x11, 0x08]) + ts_varint + bytes([0x10]) + txid
    p3 = bytes([0xAA, 0x21, 0x03, len(payload3) + 2, 0x01, 0x01, 0x80, 0x20]) + payload3
    packets.append(p3 + bytes([crc16_ccitt(payload3) & 0xFF, (crc16_ccitt(payload3) >> 8) & 0xFF]))

    # Auth 4-6: Additional exchanges
    p4 = bytes([0xAA, 0x21, 0x04, 0x0C, 0x01, 0x01, 0x80, 0x00,
                0x08, 0x04, 0x10, 0x10, 0x1A, 0x04, 0x08, 0x01, 0x10, 0x04])
    packets.append(p4 + bytes([crc16_ccitt(p4[8:]) & 0xFF, (crc16_ccitt(p4[8:]) >> 8) & 0xFF]))

    p5 = bytes([0xAA, 0x21, 0x05, 0x0C, 0x01, 0x01, 0x80, 0x00,
                0x08, 0x04, 0x10, 0x11, 0x1A, 0x04, 0x08, 0x01, 0x10, 0x04])
    packets.append(p5 + bytes([crc16_ccitt(p5[8:]) & 0xFF, (crc16_ccitt(p5[8:]) >> 8) & 0xFF]))

    p6 = bytes([0xAA, 0x21, 0x06, 0x0A, 0x01, 0x01, 0x80, 0x20,
                0x08, 0x05, 0x10, 0x12, 0x22, 0x02, 0x08, 0x01])
    packets.append(p6 + bytes([crc16_ccitt(p6[8:]) & 0xFF, (crc16_ccitt(p6[8:]) >> 8) & 0xFF]))

    # Auth 7: Final time sync
    payload7 = bytes([0x08, 0x80, 0x01, 0x10, 0x13, 0x82, 0x08, 0x11, 0x08]) + ts_varint + bytes([0x10]) + txid
    p7 = bytes([0xAA, 0x21, 0x07, len(payload7) + 2, 0x01, 0x01, 0x80, 0x20]) + payload7
    packets.append(p7 + bytes([crc16_ccitt(payload7) & 0xFF, (crc16_ccitt(payload7) >> 8) & 0xFF]))

    return packets


# =============================================================================
# Even AI Protocol (from even_ai.py)
# =============================================================================

def build_ctrl_enter(seq: int, magic: int) -> bytes:
    """CTRL(ENTER) - Enter Even AI mode. REQUIRED before ASK/REPLY."""
    payload = bytes([
        0x08, 0x01,           # commandId = 1 (CTRL)
        0x10, magic,          # magicRandom
        0x1a, 0x02,           # ctrl field (field 3)
        0x08, 0x02            # status = 2 (EVEN_AI_ENTER)
    ])
    return build_packet(seq, 0x07, 0x20, payload)


def build_ask(seq: int, magic: int, text: str) -> bytes:
    """ASK - Display question text on glasses."""
    text_bytes = text.encode('utf-8')

    askinfo = bytes([
        0x08, 0x00,           # cmdCnt = 0
        0x10, 0x00,           # streamEnable = 0
        0x18, 0x00,           # textMode = 0
        0x22,                 # text field (field 4)
    ]) + encode_varint(len(text_bytes)) + text_bytes

    payload = bytes([
        0x08, 0x03,           # commandId = 3 (ASK)
        0x10, magic,          # magicRandom
        0x2a,                 # askInfo field (field 5)
    ]) + encode_varint(len(askinfo)) + askinfo

    return build_packet(seq, 0x07, 0x20, payload)


def build_reply(seq: int, magic: int, text: str) -> bytes:
    """REPLY - Display answer text on glasses."""
    text_bytes = text.encode('utf-8')

    replyinfo = bytes([
        0x08, 0x00,           # cmdCnt = 0
        0x10, 0x00,           # streamEnable = 0
        0x18, 0x00,           # textMode = 0
        0x22,                 # text field (field 4)
    ]) + encode_varint(len(text_bytes)) + text_bytes

    payload = bytes([
        0x08, 0x05,           # commandId = 5 (REPLY)
        0x10, magic,          # magicRandom
        0x3a,                 # replyInfo field (field 7)
    ]) + encode_varint(len(replyinfo)) + replyinfo

    return build_packet(seq, 0x07, 0x20, payload)


# =============================================================================
# LLM Integration
# =============================================================================

def truncate_for_display(text: str, max_bytes: int = 200) -> str:
    """Truncate text to fit display byte limit."""
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text

    # Truncate with ellipsis
    while len(encoded) > max_bytes - 3:
        text = text[:-1]
        encoded = text.encode('utf-8')
    return text + "..."


async def query_and_display(client, provider: LLMProvider, question: str, seq: int, magic: int):
    """Query LLM and display Q&A on glasses. Returns updated seq, magic."""

    # Enter AI mode
    print(f"  Entering AI mode...")
    await client.write_gatt_char(CHAR_WRITE, build_ctrl_enter(seq, magic), response=False)
    seq += 1
    magic += 1
    await asyncio.sleep(0.3)

    # Display question
    display_q = truncate_for_display(question, 150)
    print(f"  Question: {display_q}")
    await client.write_gatt_char(CHAR_WRITE, build_ask(seq, magic, display_q), response=False)
    seq += 1
    magic += 1
    await asyncio.sleep(0.5)

    # Query LLM
    print(f"  Querying {provider.name}...")
    try:
        answer = provider.query(question, system_prompt="Be concise. Answer in 1-2 sentences.")
        display_a = truncate_for_display(answer, 200)
        print(f"  Answer: {display_a}")
    except Exception as e:
        display_a = f"Error: {str(e)[:50]}"
        print(f"  LLM Error: {e}")

    # Display answer
    await client.write_gatt_char(CHAR_WRITE, build_reply(seq, magic, display_a), response=False)
    seq += 1
    magic += 1

    return seq, magic


# =============================================================================
# Main
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description='Query AI and display on G2 glasses')
    parser.add_argument('question', nargs='?', help='Question to ask')
    parser.add_argument('-p', '--provider', default='openai',
                        choices=['openai', 'azure', 'anthropic', 'ollama'],
                        help='LLM provider (default: openai)')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Interactive mode - ask multiple questions')
    parser.add_argument('--left', action='store_true', help='Use left eye instead of right')

    args = parser.parse_args()

    print("LLM Teleprompter - AI on G2 Glasses")
    print("=" * 50)

    # Initialize provider
    try:
        provider = get_provider(args.provider)
        print(f"Provider: {provider.name}")
    except Exception as e:
        print(f"Provider error: {e}")
        print("Check your .env file for API keys")
        return

    # Connect to glasses
    print(f"\nScanning for G2 glasses...")
    devices = await BleakScanner.discover(timeout=10.0)

    pattern = "_L_" if args.left else "_R_"
    device = next((d for d in devices if d.name and "G2" in d.name and pattern in d.name), None)

    if not device:
        print("ERROR: No G2 glasses found")
        for d in devices:
            if d.name and "G2" in d.name:
                print(f"  Found: {d.name}")
        return

    print(f"  Using: {device.name}")

    async with BleakClient(device) as client:
        print("  Connected!")

        await client.start_notify(CHAR_NOTIFY, lambda s, d: None)

        # Authenticate
        print("\nAuthenticating...")
        for pkt in build_auth_packets():
            await client.write_gatt_char(CHAR_WRITE, pkt, response=False)
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        print("  Authenticated!")

        seq = 0x08
        magic = 100

        if args.interactive:
            # Interactive mode
            print("\n" + "=" * 50)
            print("Interactive mode. Type 'quit' to exit.")
            print("=" * 50 + "\n")

            while True:
                try:
                    question = input("You: ").strip()
                except EOFError:
                    break

                if question.lower() in ('quit', 'exit', 'q'):
                    break
                if not question:
                    continue

                print()
                seq, magic = await query_and_display(client, provider, question, seq, magic)
                print()
                await asyncio.sleep(3.0)
        else:
            # Single question mode
            question = args.question or "What is 2 + 2?"
            print(f"\nAsking: {question}")
            seq, magic = await query_and_display(client, provider, question, seq, magic)
            await asyncio.sleep(5.0)

        print("\n" + "=" * 50)
        print("Done! Check your glasses.")
        print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")

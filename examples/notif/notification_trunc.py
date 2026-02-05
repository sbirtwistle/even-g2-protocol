#!/usr/bin/env python3
"""
Even G2 Push Notification - Size-Limited Version

Sends push notifications with custom text to Even G2 glasses.
Automatically truncates content to fit in a single BLE packet (234 bytes max).

Usage:
    python notification_limited.py "Title" "Subtitle" "Message"
    python notification_limited.py "Sender" "Hello there!"

Requirements:
    pip install bleak
"""

import asyncio
import json
import struct
import sys
import time
from datetime import datetime
from bleak import BleakClient, BleakScanner

# BLE UUIDs for Even G2
UUID_BASE = "00002760-08c2-11e1-9073-0e8ac72e{:04x}"
CHAR_WRITE = UUID_BASE.format(0x5401)
CHAR_NOTIFY = UUID_BASE.format(0x5402)
CHAR_NOTIF_WRITE = UUID_BASE.format(0x7401)
CHAR_NOTIF_NOTIFY = UUID_BASE.format(0x7402)

# Maximum JSON size for single-packet transfer
MAX_JSON_SIZE = 234

# CRC32C (Castagnoli) lookup table
# Polynomial: 0x1EDC6F41, Init: 0, Non-reflected
CRC32C_TABLE = [
    0, 0x1edc6f41, 0x3db8de82, 0x2364b1c3,
    2071051524, 1705890373, 1187603334, 1477774535,
    4142103048, 3896448329, 3411780746, 3582446539,
    2375206668, 2471405645, 2955549070, 2935387855,
    4078607185, 3989238800, 3466741203, 3497929362,
    2288723541, 2528594196, 3050567895, 2869925782,
    0x5f9e159, 0x1b258e18, 0x38413fdb, 0x269d509a,
    2122865757, 1616130844, 1127252703, 1575808414,
    4176042467, 3862247074, 3310454625, 3683510304,
    2207835367, 2638515110, 3189783141, 2700891428,
    0xe0a23eb, 0x10d64caa, 0x33b2fd69, 0x2d6e9228,
    1971035887, 1806168494, 1220755565, 1444884268,
    0xbf3c2b2, 0x152fadf3, 0x364b1c30, 0x28977371,
    1887600566, 1851658487, 1295687988, 1407635061,
    4245731514, 3821852667, 3232261688, 3732146553,
    2254505406, 2562550527, 3151616828, 2768614525,
    4010728583, 4057117638, 3535143429, 3429526852,
    2491376003, 2325941954, 2848440065, 3072053312,
    0x19eda68f, 0x731c9ce, 0x2455780d, 0x3a89174c,
    1654397835, 2084598986, 1596245257, 1106815560,
    0x1c1447d6, 0x2c82897, 0x21ac9954, 0x3f70f615,
    1734736594, 2042205587, 1524442192, 1140935441,
    3942071774, 4096479903, 3612336988, 3381890077,
    2441511130, 2405101467, 2889768536, 3001168153,
    0x17e78564, 0x93bea25, 0x2a5f5be6, 0x348334a7,
    1821784160, 1917474593, 1362028258, 1341295011,
    3775201132, 4292382765, 3703316974, 3261091503,
    2591375976, 2225679657, 2815270122, 3104961451,
    3841793589, 4196495732, 3645227191, 3348738038,
    2676794161, 2169556080, 2721349043, 3169325810,
    0x121e643d, 0xcc20b7c, 0x2fa6babf, 0x317ad5fe,
    1768937785, 2008266360, 1423378363, 1242261754,
    3233928783, 3726489870, 4252567757, 3819267980,
    3148901195, 2775319562, 2248717769, 2564086408,
    0x3622ac47, 0x28fec306, 0xb9a72c5, 0x15461d84,
    1297289539, 1401912834, 1894502337, 1849139328,
    0x33db4d1e, 0x2d07225f, 0xe63939c, 0x10bffcdd,
    1219162138, 1450614619, 1964125848, 1808679385,
    3308795670, 3689175127, 4169197972, 3864823509,
    3192490514, 2694178131, 2213631120, 2636987345,
    0x38288fac, 0x26f4e0ed, 0x590512e, 0x1b4c3e6f,
    1129919144, 1569021417, 2128735274, 1614644075,
    3469473188, 3491207909, 4084411174, 3987686503,
    3048884384, 2875598817, 2281870882, 2531195235,
    3409057021, 3589176252, 4136290943, 3897992510,
    2957224441, 2929706680, 2382067579, 2468812858,
    0x3dd16ef5, 0x230d01b4, 0x69b077, 0x1eb5df36,
    1184945137, 1484569776, 2065173875, 1707369010,
    0x2fcf0ac8, 0x31136589, 0x1277d44a, 0xcabbb0b,
    1421785036, 1247991949, 1762027854, 2010777103,
    3643568320, 3354402689, 3834949186, 4199072003,
    2724056516, 3162612357, 2682590022, 2168028167,
    3704983961, 3255434968, 3782037275, 4289798234,
    2812554397, 3111666652, 2585588255, 2227215710,
    0x2a36eb91, 0x34ea84d0, 0x178e3513, 0x9525a52,
    1363629717, 1335572948, 1828685847, 1914955606,
    3609613099, 3388619882, 3936259497, 4098024168,
    2891443759, 2995487086, 2448371885, 2402508780,
    0x21c52923, 0x3f194662, 0x1c7df7a1, 0x2a198e0,
    1521783847, 1147730790, 1728858789, 2043684324,
    0x243cc87a, 0x3ae0a73b, 0x198416f8, 0x75879b9,
    1598911870, 1100028479, 1660267516, 2083112125,
    3537875570, 3422805299, 4016532720, 4055565233,
    2846756726, 3077726263, 2484523508, 2328542901,
]


def calc_crc32c(data: bytes) -> int:
    """Calculate CRC32C (Castagnoli) checksum."""
    crc = 0
    for b in data:
        idx = b ^ ((crc >> 24) & 0xFF)
        crc = ((crc << 8) & 0xFFFFFFFF) ^ CRC32C_TABLE[idx]
    return crc


def calc_file_check_fields(data: bytes) -> tuple[int, int, int]:
    """
    Calculate file check header fields.

    Returns (size, checksum, extra) where:
    - size = len(data) * 256
    - checksum = CRC32C << 8
    - extra = CRC32C >> 24
    """
    crc = calc_crc32c(data)
    return len(data) * 256, (crc << 8) & 0xFFFFFFFF, (crc >> 24) & 0xFF


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


def build_packet(seq: int, svc_hi: int, svc_lo: int, payload: bytes,
                 total_pkts: int = 1, pkt_num: int = 1) -> bytes:
    """Build a G2 protocol packet with header and CRC."""
    header = bytes([0xAA, 0x21, seq, len(payload) + 2, total_pkts, pkt_num, svc_hi, svc_lo])
    crc = crc16_ccitt(payload)
    return header + payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


async def authenticate(client, name: str):
    """Send authentication sequence to a G2 eye."""
    ts = int(time.time())
    ts_var = encode_varint(ts)
    txid = bytes([0xE8] + [0xFF]*8 + [0x01])

    auth_pkts = [
        build_packet(1, 0x80, 0x00, bytes([0x08,0x04,0x10,0x0D,0x1A,0x04,0x08,0x01,0x10,0x04])),
        build_packet(2, 0x80, 0x20, bytes([0x08,0x05,0x10,0x0E,0x22,0x02,0x08,0x02])),
        build_packet(3, 0x80, 0x20, bytes([0x08,0x80,0x01,0x10,0x0F,0x82,0x08,0x11,0x08]) + ts_var + bytes([0x10]) + txid),
    ]
    for p in auth_pkts:
        await client.write_gatt_char(CHAR_WRITE, p, response=False)
        await asyncio.sleep(0.1)
    print(f"  {name}: Authenticated")


def truncate_field(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding ellipsis if truncated."""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[:max_chars - 3] + "..."


def build_notification_json(title: str, subtitle: str, message: str,
                           app_id: str = "com.google.android.gm",
                           display_name: str = "Gmail",
                           max_size: int = MAX_JSON_SIZE) -> tuple[bytes, bool]:
    """
    Build notification JSON payload, truncating if necessary.

    Returns (json_bytes, was_truncated).
    """
    ts = int(time.time())

    def make_json(t, s, m):
        notif = {
            "android_notification": {
                "msg_id": 10000 + (ts % 10000),
                "action": 0,
                "app_identifier": app_id,
                "title": t,
                "subtitle": s,
                "message": m,
                "time_s": ts,
                "date": datetime.now().strftime("%Y%m%dT%H%M%S"),
                "display_name": display_name
            }
        }
        return json.dumps(notif, separators=(',', ':')).encode()

    # Try with full content first
    json_bytes = make_json(title, subtitle, message)
    if len(json_bytes) <= max_size:
        return json_bytes, False

    # Calculate overhead (JSON with empty strings)
    overhead = len(make_json("", "", ""))
    available = max_size - overhead

    # Truncate message first (priority: title > subtitle > message)
    truncated = True
    current_title = title
    current_subtitle = subtitle
    current_message = message

    # First, try removing message entirely
    if len(title) + len(subtitle) > available:
        current_message = ""
        # Still too big, truncate subtitle
        if len(title) + 3 > available:  # 3 for "..."
            current_subtitle = ""
            # Truncate title as last resort
            current_title = truncate_field(title, available)
        else:
            remaining = available - len(title)
            current_subtitle = truncate_field(subtitle, remaining)
    else:
        # Message needs truncation
        remaining = available - len(title) - len(subtitle)
        current_message = truncate_field(message, max(0, remaining))

    return make_json(current_title, current_subtitle, current_message), truncated


async def send_notification(right_client, left_client, title: str, subtitle: str, message: str):
    """Send a push notification to G2 glasses."""
    json_bytes, was_truncated = build_notification_json(title, subtitle, message)
    size, checksum, extra = calc_file_check_fields(json_bytes)

    print(f"\nSending: {title} / {subtitle}")
    if was_truncated:
        print(f"  (Content truncated to fit {MAX_JSON_SIZE} byte limit)")
    print(f"  {len(json_bytes)} bytes, checksum: 0x{checksum:08X}")

    filename = b"user/notify_whitelist.json"

    # FILE_CHECK
    fc_payload = (
        struct.pack('<I', 0x100) +
        struct.pack('<I', size) +
        struct.pack('<I', checksum) +
        bytes([extra]) +
        filename + bytes(80 - len(filename))
    )
    await right_client.write_gatt_char(CHAR_NOTIF_WRITE,
        build_packet(0x10, 0xC4, 0x00, fc_payload), response=False)
    await asyncio.sleep(0.3)

    # START
    await right_client.write_gatt_char(CHAR_NOTIF_WRITE,
        build_packet(0x49, 0xC4, 0x00, bytes([0x01])), response=False)
    await asyncio.sleep(0.1)

    # DATA (single packet - guaranteed by size limit)
    pkt = build_packet(0x49, 0xC5, 0x00, json_bytes, 1, 1)
    await right_client.write_gatt_char(CHAR_NOTIF_WRITE, pkt, response=False)
    await asyncio.sleep(0.3)

    # END
    await right_client.write_gatt_char(CHAR_NOTIF_WRITE,
        build_packet(0xDA, 0xC4, 0x00, bytes([0x02])), response=False)

    # Heartbeat to left eye
    await asyncio.sleep(0.2)
    await left_client.write_gatt_char(CHAR_WRITE,
        bytes.fromhex("aa210e0601018020080e106b6a00e174"), response=False)


async def main():
    if len(sys.argv) < 2:
        title, subtitle, message = "Python", "Test Notification", "Hello from Python!"
    elif len(sys.argv) == 2:
        title, subtitle, message = "Message", sys.argv[1], ""
    elif len(sys.argv) == 3:
        title, subtitle, message = sys.argv[1], sys.argv[2], ""
    else:
        title, subtitle, message = sys.argv[1], sys.argv[2], sys.argv[3]

    print("Even G2 Custom Notification (Size-Limited)")
    print("=" * 45)

    print("\nScanning for G2 glasses...")
    devices = await BleakScanner.discover(timeout=10.0)

    left_dev = next((d for d in devices if d.name and "G2" in d.name and "_L_" in d.name), None)
    right_dev = next((d for d in devices if d.name and "G2" in d.name and "_R_" in d.name), None)

    if not left_dev or not right_dev:
        print("ERROR: Need both G2 eyes!")
        for d in devices:
            if d.name:
                print(f"  Found: {d.name}")
        return

    print(f"  LEFT:  {left_dev.name}")
    print(f"  RIGHT: {right_dev.name}")

    async with BleakClient(left_dev) as left, BleakClient(right_dev) as right:
        print("\nConnected!")

        await left.start_notify(CHAR_NOTIF_NOTIFY, lambda s, d: None)
        await right.start_notify(CHAR_NOTIF_NOTIFY, lambda s, d: None)
        await left.start_notify(CHAR_NOTIFY, lambda s, d: None)
        await right.start_notify(CHAR_NOTIFY, lambda s, d: None)

        print("\nAuthenticating...")
        await authenticate(left, "LEFT")
        await authenticate(right, "RIGHT")
        await asyncio.sleep(0.5)

        await send_notification(right, left, title, subtitle, message)

        print("\nNotification sent!")
        await asyncio.sleep(3.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")

# Even Realities G2 Smart Glasses - Protocol Documentation

This is the result of the work of several other amazing people along with some of my own additions. Please be sure to visit the original branch and the various other forks which are referenced here.
If I've failed to properly merge / credit your work, dont hesitate to inform me, it was not intentional and no credit was meant to be taken, Im likely just incompetant.


## What the hell does that even mean???

The G2 glasses use a custom protocol created by EvenRealities. This BLE (bluetooth) protocol is used to transmit data in packets to and from the glasses. Currently, the G2 glasses are restricted to the functionality offered in the Even app - reverse engineering the BLE protocol removes this restriction.

## Status

| Feature | Status | Notes |
|---------|--------|-------|
| BLE Connection | Working | Standard BLE, no special pairing |
| Authentication | Working | 7-packet handshake sequence |
| Teleprompter | Working | Custom text display confirmed |
| Calendar Widget | Working | Display events on glasses |
| Notifications | Documented | Full ANCS-like format with actions |
| Gestures | Documented | Tap, swipe, long press detection |
| Navigation | Documented | Turn-by-turn with protobuf mapping |
| Even AI | Working | Custom Q&A display confirmed |
| Firmware/DFU | Documented | Nordic nRF52840, standard DFU protocol |
| Service 1001 | Unknown | Control/Auth channel discovered |
| Service 7450 | Documented | File transfer for notifications |

## Quick Start

```bash
cd examples/teleprompter
pip install -r requirements.txt

# Display custom text on glasses
python teleprompter.py "Hello from Python!"

# Multi-line text
python teleprompter.py "Line one
Line two
Line three"
```

## Documentation

- [BLE Services & UUIDs](docs/ble-uuids.md) - Complete characteristic mapping
- [Packet Structure](docs/packet-structure.md) - Transport layer format
- [Service Reference](docs/services.md) - All known service IDs
- [Teleprompter Protocol](docs/teleprompter.md) - Text display implementation
- [Notifications Protocol](docs/notifications.md) - Full notification format with actions
- [Gestures Protocol](docs/gestures.md) - Tap, swipe, long press detection
- [Navigation Protocol](docs/navigation.md) - Turn-by-turn navigation
- [Capture Analysis](docs/capture-analysis.md) - Raw BLE capture research notes
- [Firmware Protocol](docs/firmware-protocol.md) - DFU architecture and update mechanism
- [Firmware Format](docs/firmware-format.md) - Binary format specification
- [Even AI Protocol](docs/even-ai.md) - Custom Q&A display implementation
- [R1 Ring Analysis](docs/R1_ANALYSIS.md) - Even R1 ring BLE protocol
- [Notification File Transfer](docs/notification-file-transfer.md) - Android-style push via Service 7450

## Protocol Files

- [proto/](proto/) - Protobuf definitions for payload encoding
- [captures/](captures/) - Raw BLE capture files for analysis

## Tools

- [tools/extract_firmware.py](tools/extract_firmware.py) - Firmware package extraction and analysis

## Examples

- [examples/teleprompter/](examples/teleprompter/) - Display custom text on glasses
- [examples/even-ai/](examples/even-ai/) - Custom Q&A on Even AI card
- [examples/notif/](examples/notif/) - Push notifications to glasses

## Key Findings

### BLE Service Architecture

The G2 exposes 4 custom services, each with a Write (x401) and Notify (x402) characteristic:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Control   │  │   Content   │  │  Rendering  │  │   Unknown   │
│    1001     │  │    5450     │  │    6450     │  │    7450     │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ 0001 (W)    │  │ 5401 (W)    │  │ 6401 (W)    │  │ 7401 (W)    │
│ 0002 (N)    │  │ 5402 (N)    │  │ 6402 (N)    │  │ 7402 (N)    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

Plus standard services: Device Info (0x180A), Nordic UART (NUS)

### Channel Purposes

| Service | Purpose | Packet Format |
|---------|---------|---------------|
| 1001 | Control/Authentication | TBD |
| 5450 | Content (what to display) | `0xAA` header, protobuf payload |
| 6450 | Rendering (how to display) | Different format, possibly encrypted |
| 7450 | Unknown | TBD |

### CRC Algorithm (Content Channel)

- **Type**: CRC-16/CCITT
- **Init**: 0xFFFF
- **Polynomial**: 0x1021
- **Scope**: Calculated over payload bytes only (skip 8-byte header)
- **Format**: Little-endian

### Content Channel Packet Structure

```
[AA] [21] [seq] [len] [01] [01] [svc_hi] [svc_lo] [payload...] [crc_lo] [crc_hi]
```

### Rendering Channel (6402) Observations

From capture analysis:
- 205-byte fixed packets at ~11-12 Hz
- Data does NOT use `0xAA` header format
- Appears encrypted or differently encoded
- Sequence counter in last byte (wraps 0x00-0xFF)

## Contributing

Pull requests welcome! Areas needing research:

**High Priority:**

- Rendering channel (6402) encryption/encoding
- Service 1001 purpose and protocol

**In Progress:**

- Translation feature
- R1 Ring full protocol mapping

## Credits

- Protocol research by the Even Realities community

## Disclaimer

This is an unofficial community project for educational purposes. Not affiliated with Even Realities.

## Discord

For all communications, I recommend Discord. Join the [EvenRealities Discord Server](https://discord.gg/arDkX3pr), which contains a reverse engineering channel containing many threads, including G2 RE.

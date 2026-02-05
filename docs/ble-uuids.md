# Even G2 BLE UUIDs & Characteristics

## Overview

The G2 uses a two-layer architecture:

1. **BLE Layer** (this document): GATT services and characteristics for data transport
2. **Protocol Layer** (see [services.md](services.md)): Service IDs within packet payloads

The G2 glasses expose multiple BLE services following a consistent pattern:
- **x401** characteristics: Write with Response (commands to glasses)
- **x402** characteristics: Notify (responses/data from glasses)

## G2 Custom Services

**Base UUID**: `00002760-08c2-11e1-9073-0e8ac72e{xxxx}`

### Service Summary

| Service UUID Suffix | Write Char | Notify Char | Purpose |
|---------------------|------------|-------------|---------|
| **1001** | 0001 | 0002 | Control/Authentication |
| **5450** | 5401 | 5402 | Content Channel |
| **6450** | 6401 | 6402 | Rendering Channel |
| **7450** | 7401 | 7402 | Unknown (TBD) |

---

### Service 1001 - Control/Authentication

| Characteristic | UUID Suffix | Properties | Purpose |
|----------------|-------------|------------|---------|
| Write | 0001 | Write with Response, Read | Commands |
| Notify | 0002 | Notify | Responses |

**Status**: Under investigation. Possibly used for authentication handshake or device control.

---

### Service 5450 - Content Channel

| Characteristic | UUID Suffix | Properties | Purpose |
|----------------|-------------|------------|---------|
| Write | 5401 | Write with Response, Read | Send content commands |
| Notify | 5402 | Notify | Receive content responses |

**Purpose**: Transmits *what* to display (text, data, calendar events, notifications).

**Packet Format**: Uses documented `0xAA` header structure:
```
[AA] [21] [seq] [len] [01] [01] [svc_hi] [svc_lo] [payload...] [crc_lo] [crc_hi]
```

---

### Service 6450 - Rendering Channel

| Characteristic | UUID Suffix | Properties | Purpose |
|----------------|-------------|------------|---------|
| Write | 6401 | Write with Response, Read | Send rendering commands |
| Notify | 6402 | Notify | Receive rendering data |

**Purpose**: Controls *how* content is displayed (positioning, styling, display updates).

**Observed Behavior** (from capture analysis 2026-02-05):
- High-frequency notifications (~11-12 packets/second)
- Fixed packet size: 205 bytes
- Data appears encrypted or uses different encoding than Content Channel
- Last byte is sequence counter (wraps 0x00-0xFF)
- Trailer patterns observed: `00 00 00`, `00 08 00`, `00 11 00`, `00 1B 00`

**Note**: Navigation and Even AI features show high traffic on this channel.

---

### Service 7450 - Unknown

| Characteristic | UUID Suffix | Properties | Purpose |
|----------------|-------------|------------|---------|
| Write | 7401 | Write with Response, Read | Unknown |
| Notify | 7402 | Notify | Unknown |

**Status**: Undocumented. Purpose unknown - needs investigation.

---

## Standard BLE Services

### Device Information Service (0x180A)

| Characteristic | UUID | Properties | Purpose |
|----------------|------|------------|---------|
| Manufacturer Name | 2A29 | Read | "Even Realities" |
| Model Number | 2A24 | Read | Model identifier |
| Serial Number | 2A25 | Read | Device serial |
| Firmware Revision | 2A26 | Read | Firmware version |
| Hardware Revision | 2A27 | Read | Hardware version |

---

### Nordic UART Service (NUS)

**Service UUID**: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`

| Characteristic | UUID | Properties | Purpose |
|----------------|------|------------|---------|
| TX (to device) | 6e400002-... | Write, Write with Response | Send data |
| RX (from device) | 6e400003-... | Notify | Receive data |

**Purpose**: Standard serial-over-BLE service. Possibly used for:
- Firmware updates
- Debug/diagnostic interface
- Factory configuration

---

## Full UUID Reference

### G2 Custom Characteristics

| Short UUID | Full UUID | Service | Direction |
|------------|-----------|---------|-----------|
| 0001 | `00002760-08c2-11e1-9073-0e8ac72e0001` | 1001 | Write |
| 0002 | `00002760-08c2-11e1-9073-0e8ac72e0002` | 1001 | Notify |
| 5401 | `00002760-08c2-11e1-9073-0e8ac72e5401` | 5450 | Write |
| 5402 | `00002760-08c2-11e1-9073-0e8ac72e5402` | 5450 | Notify |
| 6401 | `00002760-08c2-11e1-9073-0e8ac72e6401` | 6450 | Write |
| 6402 | `00002760-08c2-11e1-9073-0e8ac72e6402` | 6450 | Notify |
| 7401 | `00002760-08c2-11e1-9073-0e8ac72e7401` | 7450 | Write |
| 7402 | `00002760-08c2-11e1-9073-0e8ac72e7402` | 7450 | Notify |

---

## ATT Handle Mapping

ATT handles vary per connection, but typical mappings observed:

| ATT Handle | UUID Suffix | Service | Purpose |
|------------|-------------|---------|---------|
| `0x0021` | N/A | ANCS-like | Notification data |
| `0x0842` | 5401 | 5450 | Content Write |
| `0x0844` | 5402 | 5450 | Content Notify |
| `0x0864` | 6402 | 6450 | Rendering Notify (map data) |

> **Note**: Handle `0x0021` is for ANCS-like notifications, separate from G2 custom services.
> See [notifications.md](notifications.md) for the notification protocol.

---

## Connection Parameters

```
Connection Interval: 7.5ms - 30ms (typical)
Slave Latency: 0
Supervision Timeout: 2000ms
MTU: 512 bytes
```

---

## Device Naming

G2 glasses advertise with names like:
- `Even G2_XX_L_YYYYYY` (Left)
- `Even G2_XX_R_YYYYYY` (Right)

Where:
- `XX` = Model variant
- `L/R` = Left/Right ear
- `YYYYYY` = Serial suffix

---

## Authentication

The G2 uses **custom application-level authentication** rather than BLE pairing/bonding:
- No PIN required
- No secure pairing
- Session established via 7-packet handshake on Content Channel (5401/5402)
- Timestamp + transaction ID exchange

---

## Channel Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Even G2 BLE Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Control   │  │   Content   │  │  Rendering  │  │ Unknown │ │
│  │    1001     │  │    5450     │  │    6450     │  │  7450   │ │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────┤ │
│  │ 0001 (W)    │  │ 5401 (W)    │  │ 6401 (W)    │  │ 7401 (W)│ │
│  │ 0002 (N)    │  │ 5402 (N)    │  │ 6402 (N)    │  │ 7402 (N)│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                                   │
│  W = Write with Response    N = Notify                           │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Standard Services: Device Info (180A), Nordic UART (NUS)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Research Notes

### Rendering Channel (6402) Capture Analysis

From capture dated 2026-02-05:
- **Duration**: ~40 seconds
- **Packets**: 456 total
- **Rate**: ~11-12 packets/second
- **Size**: 205 bytes per packet
- **Format**: Does NOT match standard `0xAA` packet structure
- **Encryption**: Data appears encrypted or differently encoded

**Trailer byte patterns observed**:
| Pattern | Frequency | Possible Meaning |
|---------|-----------|------------------|
| `00 00 00 [seq]` | Common | Standard frame? |
| `00 08 00 [seq]` | Periodic | Flag/status? |
| `00 11 00 [seq]` | Occasional | TBD |
| `00 1B 00 [seq]` | Occasional | TBD |
| `00 25 00 [seq]` | Rare | TBD |
| `00 F8 FF [seq]` | Rare | Special marker? |

**Open Questions**:
1. Is 6402 data encrypted? With what key?
2. What triggers high-frequency rendering traffic?
3. How do Content (5401) and Rendering (6401) channels coordinate?

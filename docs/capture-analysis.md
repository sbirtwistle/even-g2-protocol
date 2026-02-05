# BLE Capture Analysis

This document contains analysis of raw BLE captures from the Even G2 glasses.

## Capture: 2026-02-05 Rendering Channel (6402)

**File**: `captures/Untitled.txt`

### Summary

| Property | Value |
|----------|-------|
| Characteristic | 6402 (Rendering Channel - Notify) |
| Direction | Incoming only (glasses → phone) |
| Duration | ~40 seconds (13:30:28 to 13:31:08) |
| Total Packets | 456 |
| Packet Rate | ~11-12 packets/second |
| Packet Size | 205 bytes (fixed) |

### Key Finding: Different Packet Format

The 6402 data does **NOT** use the standard `0xAA` header format documented for the Content Channel (5401/5402).

**Content Channel format:**
```
[AA] [21] [seq] [len] [01] [01] [svc_hi] [svc_lo] [payload...] [crc_lo] [crc_hi]
```

**Rendering Channel (6402) observed:**
```
[random bytes...] [trailer] [seq]
```

First bytes appear random/encrypted. No `0xAA` magic byte detected.

### Packet Structure Analysis

#### Sequence Counter (Last Byte)

The final byte is a sequence counter that increments and wraps:

```
...D8, D9, DA, DB, DC, DD, DE, DF, E0...
...FD, FE, FF, 00, 01, 02, 03...
```

#### Trailer Patterns (Bytes N-4 to N-1)

Consistent patterns observed before the sequence byte:

| Pattern | Count | Frequency | Hypothesis |
|---------|-------|-----------|------------|
| `00 00 00 [seq]` | ~300 | 66% | Standard data frame |
| `00 08 00 [seq]` | ~80 | 18% | Status/flag type 1 |
| `00 11 00 [seq]` | ~30 | 7% | Status/flag type 2 |
| `00 1B 00 [seq]` | ~20 | 4% | Status/flag type 3 |
| `00 25 00 [seq]` | ~10 | 2% | Rare marker |
| `00 F8 FF [seq]` | ~5 | 1% | Special/error marker? |

The second byte in the trailer (`00`, `08`, `11`, `1B`, `25`, `F8`) may indicate:
- Frame type or subtype
- Status flags
- Data length indicator
- Error/acknowledgment codes

#### Internal Patterns (Positions 35-40)

Repeating byte patterns observed mid-packet:

```
85 xx    (common)
C5 xx    (common)
81 xx    (occasional)
C1 xx    (occasional)
```

These could indicate:
- Block cipher boundaries (if encrypted)
- Embedded headers within payload
- Fixed structure markers

### Data Characteristics

#### Encryption Hypothesis

Evidence suggesting encryption:
1. First bytes appear random (no constant magic bytes)
2. High entropy throughout packet body
3. Repeating patterns at fixed intervals (possible block cipher)
4. Only trailer bytes show clear structure

Possible encryption schemes:
- AES-128/256 in CBC or CTR mode
- XOR with rolling key
- Custom cipher

#### Frame Rate Analysis

```
Timestamp deltas (ms):
23, 62, 59, 30, 60, 90, 2, 59, 59, 30...

Average: ~60ms between packets
Rate: ~16-17 packets/second peak, ~11-12 sustained
```

High frequency suggests real-time display updates (video-like refresh).

### Context Hypothesis

This capture likely represents one of:

1. **Even AI Response Stream**
   - AI-generated content being rendered
   - Would explain high bandwidth and encryption

2. **Navigation Display**
   - Turn-by-turn graphics
   - Map rendering data

3. **Screen Mirroring/Casting**
   - Phone screen content
   - Would require high bandwidth

### Missing Data

**No outgoing (OUT) packets captured** - we don't know:
- What command triggered this stream
- Protocol on 6401 (write characteristic)
- How to initiate/control the stream

### Next Steps

1. **Capture 6401 writes** - Commands that trigger 6402 responses
2. **Capture during known activities**:
   - Start Even AI and capture
   - Start navigation and capture
   - Compare packet patterns
3. **Analyze encryption**:
   - Look for key exchange in auth handshake
   - Check if Service 1001 handles keys
4. **Correlate with Content Channel**:
   - Does 5401/5402 activity precede 6402 bursts?

---

## Capture Template

When adding new captures, document:

```markdown
## Capture: [DATE] [Description]

**File**: `captures/[filename]`

### Summary
| Property | Value |
|----------|-------|
| Characteristic | |
| Direction | |
| Duration | |
| Total Packets | |
| Context | (what was happening on the glasses) |

### Observations
[Key findings]

### Raw Sample
[First few packets in hex]
```

---

## Tools

### Capture Format

Captures should be in the format:
```
[timestamp] IN/OUT [characteristic]
  Hex: [space-separated hex bytes]
```

### Analysis Commands

Count packets:
```bash
grep -c "IN  6402" captures/file.txt
```

Extract trailer bytes:
```bash
grep "Hex:" captures/file.txt | awk '{print $(NF-3), $(NF-2), $(NF-1), $NF}'
```

Extract first N bytes:
```bash
grep "Hex:" captures/file.txt | while read line; do
  echo "$line" | sed 's/.*Hex: //' | awk '{print $1, $2, $3, $4, $5}'
done
```

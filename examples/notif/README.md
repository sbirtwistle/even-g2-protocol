# Push Notifications

Send custom push notifications to Even G2 glasses.

## Scripts

### notification.py

Full-featured notification sender. Supports multi-packet transfers for longer messages.

```bash
python notification.py "Title" "Subtitle" "Message body"
python notification.py "Sender" "Subject line"
python notification.py "Quick message"
```

> **Work In Progress**: Messages exceeding ~234 bytes (the single-packet limit) currently fail silently. Multi-packet reassembly on the glasses side is still under investigation. For reliable delivery, use `notification_trunc.py` or keep messages short.

### notification_trunc.py

Size-limited version that guarantees delivery by truncating content to fit in a single BLE packet.

```bash
python notification_trunc.py "Title" "Subtitle" "Long message that will be truncated..."
```

**Truncation priority** (least to most important):
1. Message (truncated first)
2. Subtitle
3. Title (preserved as much as possible)

Truncated fields show "..." at the end.

## Protocol Overview

Notifications use the **File Transfer** protocol on the 0x74xx characteristics:

1. **FILE_CHECK** (0xC4-00): Announce file with size and CRC32C checksum
2. **START** (0xC4-00, payload 0x01): Begin transfer
3. **DATA** (0xC5-00): Send JSON payload (234 bytes max per packet)
4. **END** (0xC4-00, payload 0x02): Complete transfer

### JSON Format

```json
{
  "android_notification": {
    "msg_id": 12345,
    "action": 0,
    "app_identifier": "com.google.android.gm",
    "title": "Sender Name",
    "subtitle": "Subject Line",
    "message": "Body text",
    "time_s": 1704067200,
    "date": "20240101T120000",
    "display_name": "Gmail"
  }
}
```

### Checksum

The CRC32C checksum is split across two fields in the FILE_CHECK header:

```python
crc = calc_crc32c(json_bytes)
size = len(json_bytes) * 256
checksum = (crc << 8) & 0xFFFFFFFF  # Lower 24 bits shifted
extra = (crc >> 24) & 0xFF          # High byte
```

## Known Issues

- **Multi-packet transfers**: Messages >234 bytes fail. The glasses may not properly reassemble chunked data, or the packet framing may be incorrect. Under investigation.

- **Whitelisting**: The filename `user/notify_whitelist.json` suggests app whitelisting exists. The exact mechanism is undocumented.

- **Cache behavior**: The glasses cache notifications by checksum. Sending the same content twice may show cached version instead of re-displaying.

## Requirements

```bash
pip install bleak
```

Or from repo root:
```bash
pip install -r requirements.txt
```

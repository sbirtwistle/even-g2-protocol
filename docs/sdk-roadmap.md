# Implementation Roadmap: Full Mentraos Integration

This document provides step-by-step instructions for closing all protocol gaps and achieving full Mentraos integration.

---

## Phase 1: Traffic Capture Setup

Before implementing any new features, you need the ability to capture BLE traffic.

### Android Setup (Recommended)

```bash
# 1. Enable Developer Options on your Android device
#    Settings → About Phone → Tap "Build Number" 7 times

# 2. Enable Bluetooth HCI Snoop Log
#    Settings → Developer Options → Enable Bluetooth HCI snoop log

# 3. After using a feature on glasses, pull the log:
adb pull /data/misc/bluetooth/logs/btsnoop_hci.log ./captures/

# 4. Convert to readable format with Wireshark or btmon
wireshark btsnoop_hci.log
# Filter: bluetooth.dst == "XX:XX:XX:XX:XX:XX" (your glasses MAC)
```

### Alternative: nRF Connect (Real-time)

```
1. Install nRF Connect on Android
2. Connect to G2 glasses
3. Subscribe to notifications on 0x5402
4. Use official Even app feature
5. Watch packets in nRF Connect log
```

---

## Phase 2: Even AI Implementation

**Priority: HIGH** | **Estimated Captures Needed: 2-3 sessions**

### Step 2.1: Capture AI Traffic

```bash
# Capture session:
1. Enable BLE snoop logging
2. Open Even app
3. Trigger Even AI feature (voice command or button)
4. Ask a simple question: "What time is it?"
5. Wait for response
6. Ask follow-up: "Tell me a joke"
7. End session
8. Pull btsnoop log
```

### Step 2.2: Identify Service ID

Look for packets after auth with unknown service IDs. Expected pattern:
```
AA 21 XX XX 01 01 [??] [??] ...
                   ↑    ↑
            Unknown service = likely AI
```

Common candidates: `0x0A-20`, `0x12-20`, `0x15-20`

### Step 2.3: Decode Request Format

Create analysis script:

```python
#!/usr/bin/env python3
"""ai_decoder.py - Analyze AI request packets"""

import sys

def decode_varint(data, offset):
    """Decode protobuf varint, return (value, new_offset)"""
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, offset

def analyze_packet(hex_string):
    """Analyze a captured AI packet"""
    data = bytes.fromhex(hex_string.replace(" ", ""))

    # Skip header (8 bytes) and CRC (2 bytes)
    payload = data[8:-2]

    print(f"Service ID: 0x{data[6]:02X}-{data[7]:02X}")
    print(f"Payload length: {len(payload)}")
    print(f"Payload hex: {payload.hex()}")

    # Try to decode as protobuf
    offset = 0
    while offset < len(payload):
        field_byte = payload[offset]
        field_num = field_byte >> 3
        wire_type = field_byte & 0x07
        offset += 1

        if wire_type == 0:  # Varint
            value, offset = decode_varint(payload, offset)
            print(f"  Field {field_num} (varint): {value}")
        elif wire_type == 2:  # Length-delimited
            length, offset = decode_varint(payload, offset)
            value = payload[offset:offset+length]
            offset += length
            try:
                text = value.decode('utf-8')
                print(f"  Field {field_num} (string): {text}")
            except:
                print(f"  Field {field_num} (bytes): {value.hex()}")

if __name__ == "__main__":
    # Paste captured packet hex here
    packet = sys.argv[1] if len(sys.argv) > 1 else input("Packet hex: ")
    analyze_packet(packet)
```

### Step 2.4: Expected AI Protocol Structure

Based on similar devices, expect:

```protobuf
// proto/ai_service.proto (to be verified)
message AIRequest {
    uint32 type = 1;           // 0x01 = query, 0x02 = cancel
    uint32 msg_id = 2;
    string prompt = 3;         // User's question
    uint32 context_id = 4;     // For follow-up questions
}

message AIResponse {
    uint32 type = 1;           // 0x01 = partial, 0x02 = complete
    uint32 msg_id = 2;
    string text = 3;           // AI response text
    bool is_final = 4;
}
```

### Step 2.5: Build AI Service Implementation

```python
# examples/ai/ai_query.py

def build_ai_request(seq: int, msg_id: int, prompt: str) -> bytes:
    """Build AI query packet (SERVICE_ID to be determined from capture)"""
    prompt_bytes = prompt.encode('utf-8')

    payload = (
        bytes([0x08, 0x01]) +                    # type = 1 (query)
        bytes([0x10]) + encode_varint(msg_id) +  # msg_id
        bytes([0x1A]) + encode_varint(len(prompt_bytes)) + prompt_bytes  # prompt
    )

    # Replace 0x??, 0x?? with actual service ID from capture
    return build_packet(seq, 0x??, 0x??, payload)


async def ai_query(client, prompt: str):
    """Send AI query and collect responses"""
    responses = []

    async def on_notify(sender, data):
        # Parse AI response packets
        if data[6:8] == bytes([AI_SERVICE_HI, AI_SERVICE_LO]):
            responses.append(parse_ai_response(data))

    await client.start_notify(CHAR_NOTIFY, on_notify)

    # Send query
    await client.write_gatt_char(CHAR_WRITE, build_ai_request(seq, msg_id, prompt))

    # Wait for final response
    while not responses or not responses[-1].is_final:
        await asyncio.sleep(0.1)

    return "".join(r.text for r in responses)
```

### Step 2.6: Test and Validate

```bash
# Test with simple queries
python ai_query.py "What is 2+2?"
python ai_query.py "Tell me the weather"

# Test streaming responses
python ai_query.py "Write a short poem"

# Test conversation context
python ai_query.py --context "What was my previous question?"
```

---

## Phase 3: Navigation Protocol

**Priority: HIGH** | **Estimated Captures Needed: 3-5 sessions**

### Step 3.1: Capture Navigation Traffic

```bash
# Capture session:
1. Enable BLE snoop logging
2. Open a navigation app (Google Maps, Apple Maps)
3. Start navigation to a destination 5+ minutes away
4. Complete the route (or significant portion)
5. Pull btsnoop log
6. Repeat with different route types (highway, local, walking)
```

### Step 3.2: Identify Packet Patterns

Navigation likely uses high-frequency updates. Look for:
- Packets sent every 1-5 seconds during active navigation
- Service ID consistent throughout navigation
- Payload size varying with instruction complexity

### Step 3.3: Expected Navigation Structure

```protobuf
// proto/navigation_service.proto (to be verified)
message NavigationUpdate {
    uint32 type = 1;              // Update type
    uint32 msg_id = 2;
    NavigationInstruction instruction = 3;
}

message NavigationInstruction {
    ManeuverType maneuver = 1;    // Turn type
    string road_name = 2;         // "Main Street"
    uint32 distance_meters = 3;   // Distance to maneuver
    string distance_text = 4;     // "500 ft" or "0.3 mi"
    uint32 eta_seconds = 5;       // ETA to destination
}

enum ManeuverType {
    STRAIGHT = 0;
    TURN_LEFT = 1;
    TURN_RIGHT = 2;
    SLIGHT_LEFT = 3;
    SLIGHT_RIGHT = 4;
    SHARP_LEFT = 5;
    SHARP_RIGHT = 6;
    U_TURN = 7;
    ROUNDABOUT = 8;
    DESTINATION = 9;
}
```

### Step 3.4: Build Navigation Implementation

```python
# examples/navigation/nav_display.py

MANEUVER_ICONS = {
    0: "↑",   # Straight
    1: "←",   # Turn left
    2: "→",   # Turn right
    3: "↖",   # Slight left
    4: "↗",   # Slight right
    5: "⤺",   # Sharp left
    6: "⤻",   # Sharp right
    7: "↩",   # U-turn
    8: "⟳",   # Roundabout
    9: "🏁",  # Destination
}

def build_nav_update(seq: int, msg_id: int, maneuver: int,
                     road: str, distance: str) -> bytes:
    """Build navigation update packet"""
    road_bytes = road.encode('utf-8')
    dist_bytes = distance.encode('utf-8')

    instruction = (
        bytes([0x08]) + encode_varint(maneuver) +
        bytes([0x12]) + encode_varint(len(road_bytes)) + road_bytes +
        bytes([0x22]) + encode_varint(len(dist_bytes)) + dist_bytes
    )

    payload = (
        bytes([0x08, 0x01]) +                    # type
        bytes([0x10]) + encode_varint(msg_id) +  # msg_id
        bytes([0x1A]) + encode_varint(len(instruction)) + instruction
    )

    return build_packet(seq, NAV_SERVICE_HI, NAV_SERVICE_LO, payload)
```

---

## Phase 4: Display Rendering (0x6402)

**Priority: MEDIUM-HIGH** | **Captures: Use existing teleprompter captures**

### Step 4.1: Analyze Existing Captures

The 0x6402 channel appears in teleprompter traffic. Extract and analyze:

```python
# tools/analyze_rendering.py

def extract_6402_packets(btsnoop_file):
    """Extract all rendering channel packets"""
    # Parse btsnoop, filter for 0x6402 characteristic writes
    # Return list of payloads
    pass

def analyze_204_byte_packet(data):
    """Analyze 204-byte rendering command structure"""
    print(f"Total length: {len(data)}")

    # Look for patterns
    # Hypothesis: [command_type][coordinates][data]

    # First few bytes likely command type
    print(f"Header (first 8 bytes): {data[:8].hex()}")

    # Look for coordinate patterns (usually 2-4 bytes each)
    # X, Y coordinates might be at fixed offsets

    # Check for repeating structures
    for i in range(0, len(data), 4):
        chunk = data[i:i+4]
        if len(chunk) == 4:
            # Interpret as coordinates or values
            val1 = int.from_bytes(chunk[:2], 'little')
            val2 = int.from_bytes(chunk[2:4], 'little')
            print(f"  Offset {i}: {val1}, {val2}")
```

### Step 4.2: Expected Display Command Structure

```
[1 byte]  Command type (0x01=clear, 0x02=draw, 0x03=refresh?)
[2 bytes] X coordinate (little-endian)
[2 bytes] Y coordinate (little-endian)
[2 bytes] Width
[2 bytes] Height
[N bytes] Pixel data or text reference
[2 bytes] CRC
```

### Step 4.3: Build Rendering Primitives

```python
# src/display/rendering.py

class DisplayRenderer:
    def __init__(self, client):
        self.client = client
        self.seq = 0

    def clear_display(self) -> bytes:
        """Clear entire display"""
        return self._build_render_cmd(0x01, 0, 0, 640, 480, b'')

    def draw_text(self, x: int, y: int, text: str, font_size: int = 5) -> bytes:
        """Draw text at position"""
        text_bytes = text.encode('utf-8')
        return self._build_render_cmd(0x02, x, y, len(text) * 8, font_size * 2, text_bytes)

    def draw_rect(self, x: int, y: int, w: int, h: int, filled: bool = False) -> bytes:
        """Draw rectangle"""
        cmd = 0x04 if filled else 0x03
        return self._build_render_cmd(cmd, x, y, w, h, b'')

    def _build_render_cmd(self, cmd: int, x: int, y: int, w: int, h: int, data: bytes) -> bytes:
        payload = bytes([cmd])
        payload += x.to_bytes(2, 'little')
        payload += y.to_bytes(2, 'little')
        payload += w.to_bytes(2, 'little')
        payload += h.to_bytes(2, 'little')
        payload += data

        # Pad to 204 bytes if required
        if len(payload) < 202:
            payload += bytes(202 - len(payload))

        return add_crc(bytes([0xAA, 0x21, self.seq, len(payload)+2, 0x01, 0x01, 0x64, 0x02]) + payload)
```

---

## Phase 5: Error Handling

**Priority: HIGH** | **Captures: Intentionally trigger errors**

### Step 5.1: Trigger Error Conditions

```bash
# Test scenarios:
1. Send malformed packet (bad CRC)
2. Send packet with invalid service ID
3. Send out-of-sequence packets
4. Disconnect mid-transmission
5. Send oversized payload
6. Rapid-fire packets (rate limiting)
```

### Step 5.2: Document Error Response Format

```python
# Expected error response structure
class ErrorResponse:
    service_id: tuple[int, int]  # Original service
    error_code: int              # Error type
    error_message: str           # Optional description

ERROR_CODES = {
    0x01: "Invalid CRC",
    0x02: "Unknown service",
    0x03: "Sequence error",
    0x04: "Payload too large",
    0x05: "Rate limited",
    0x06: "Not authenticated",
    0x07: "Invalid state",
}
```

### Step 5.3: Implement Error Handling

```python
# src/protocol/error_handler.py

class G2ErrorHandler:
    def __init__(self):
        self.retry_counts = {}
        self.max_retries = 3

    async def handle_error(self, error_code: int, context: dict) -> bool:
        """Handle error, return True if should retry"""

        if error_code == 0x01:  # Bad CRC
            # Recalculate and resend
            return True

        elif error_code == 0x03:  # Sequence error
            # Reset sequence counter
            self.reset_sequence()
            return True

        elif error_code == 0x05:  # Rate limited
            # Back off exponentially
            await asyncio.sleep(2 ** self.retry_counts.get(context['msg_id'], 0))
            return True

        elif error_code == 0x06:  # Not authenticated
            # Re-authenticate
            await self.reauthenticate()
            return True

        return False
```

---

## Phase 6: SDK Architecture

### Directory Structure

```
mentraos-g2-sdk/
├── pyproject.toml
├── README.md
├── src/
│   └── mentraos_g2/
│       ├── __init__.py
│       ├── client.py           # High-level client
│       ├── connection/
│       │   ├── __init__.py
│       │   ├── scanner.py      # Device discovery
│       │   ├── ble.py          # Low-level BLE
│       │   └── auth.py         # Authentication
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── packet.py       # Packet building
│       │   ├── crc.py          # CRC calculation
│       │   ├── varint.py       # Protobuf encoding
│       │   └── errors.py       # Error handling
│       ├── services/
│       │   ├── __init__.py
│       │   ├── base.py         # Service base class
│       │   ├── teleprompter.py
│       │   ├── dashboard.py
│       │   ├── display.py
│       │   ├── ai.py           # When ready
│       │   └── navigation.py   # When ready
│       └── models/
│           ├── __init__.py
│           └── messages.py     # Data classes
├── tests/
│   ├── test_packet.py
│   ├── test_crc.py
│   └── test_services.py
└── examples/
    ├── simple_text.py
    ├── calendar_widget.py
    └── ai_assistant.py
```

### High-Level Client API

```python
# src/mentraos_g2/client.py

class G2Client:
    """High-level client for Even G2 glasses"""

    def __init__(self):
        self._connection = None
        self._services = {}

    async def connect(self, device_name: str = None, prefer_side: str = "left"):
        """Connect to G2 glasses"""
        scanner = G2Scanner()
        device = await scanner.find(device_name, prefer_side)

        self._connection = G2Connection(device)
        await self._connection.connect()
        await self._connection.authenticate()

        # Initialize services
        self._services['teleprompter'] = TeleprompterService(self._connection)
        self._services['dashboard'] = DashboardService(self._connection)
        self._services['display'] = DisplayService(self._connection)

    async def disconnect(self):
        """Disconnect from glasses"""
        await self._connection.disconnect()

    @property
    def teleprompter(self) -> TeleprompterService:
        return self._services['teleprompter']

    @property
    def dashboard(self) -> DashboardService:
        return self._services['dashboard']

    @property
    def display(self) -> DisplayService:
        return self._services['display']

    # Context manager support
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()


# Usage example
async def main():
    async with G2Client() as glasses:
        # Display text
        await glasses.teleprompter.show("Hello, World!")

        # Show calendar
        await glasses.dashboard.show_calendar([
            {"title": "Meeting", "time": "10:00 AM"},
            {"title": "Lunch", "time": "12:30 PM"},
        ])

        # Custom rendering (when ready)
        await glasses.display.clear()
        await glasses.display.draw_text(100, 50, "Custom UI")
```

### Service Base Class

```python
# src/mentraos_g2/services/base.py

class BaseService:
    """Base class for G2 services"""

    SERVICE_ID: tuple[int, int] = (0x00, 0x00)

    def __init__(self, connection: G2Connection):
        self._conn = connection
        self._msg_id = 0x14

    def _next_msg_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _send(self, payload: bytes) -> None:
        """Send packet to glasses"""
        packet = build_packet(
            self._conn.next_seq(),
            self.SERVICE_ID[0],
            self.SERVICE_ID[1],
            payload
        )
        await self._conn.write(packet)

    async def _send_and_wait(self, payload: bytes, response_type: int) -> bytes:
        """Send packet and wait for response"""
        future = asyncio.Future()

        def on_response(data):
            if self._is_response(data, response_type):
                future.set_result(data)

        self._conn.add_listener(on_response)
        await self._send(payload)

        try:
            return await asyncio.wait_for(future, timeout=5.0)
        finally:
            self._conn.remove_listener(on_response)
```

---

## Phase 7: Testing & Validation

### Unit Tests

```python
# tests/test_packet.py

def test_crc_calculation():
    payload = bytes([0x08, 0x01, 0x10, 0x14])
    expected_crc = 0x1234  # Known value
    assert crc16_ccitt(payload) == expected_crc

def test_packet_building():
    packet = build_packet(0x01, 0x06, 0x20, bytes([0x08, 0x01]))
    assert packet[0] == 0xAA  # Magic
    assert packet[1] == 0x21  # Type
    assert packet[2] == 0x01  # Sequence
    assert packet[6:8] == bytes([0x06, 0x20])  # Service ID

def test_varint_encoding():
    assert encode_varint(1) == bytes([0x01])
    assert encode_varint(127) == bytes([0x7F])
    assert encode_varint(128) == bytes([0x80, 0x01])
    assert encode_varint(300) == bytes([0xAC, 0x02])
```

### Integration Tests

```python
# tests/test_integration.py

@pytest.mark.asyncio
async def test_connect_and_auth():
    async with G2Client() as client:
        assert client.is_connected
        assert client.is_authenticated

@pytest.mark.asyncio
async def test_teleprompter_display():
    async with G2Client() as client:
        result = await client.teleprompter.show("Test message")
        assert result.success
```

### Mock Server for Development

```python
# tests/mock_server.py

class MockG2Server:
    """Mock G2 glasses for testing without hardware"""

    def __init__(self):
        self.authenticated = False
        self.received_packets = []

    async def handle_packet(self, data: bytes) -> bytes:
        """Process packet and return response"""
        self.received_packets.append(data)

        service = (data[6], data[7])

        if service == (0x80, 0x00):
            return self._handle_auth(data)
        elif service == (0x06, 0x20):
            return self._handle_teleprompter(data)

        return self._error_response(0x02)  # Unknown service
```

---

## Implementation Checklist

### Phase 1: Setup
- [ ] Set up Android BLE snoop logging
- [ ] Test capture with teleprompter feature
- [ ] Create packet analysis tools

### Phase 2: Even AI
- [ ] Capture AI session traffic
- [ ] Identify AI service ID
- [ ] Decode request format
- [ ] Decode response format (including streaming)
- [ ] Add protobuf definitions
- [ ] Build example implementation
- [ ] Test various query types

### Phase 3: Navigation
- [ ] Capture navigation traffic (multiple routes)
- [ ] Identify navigation service ID
- [ ] Decode maneuver encoding
- [ ] Decode distance/ETA format
- [ ] Add protobuf definitions
- [ ] Build example implementation

### Phase 4: Display Rendering
- [ ] Analyze 0x6402 packets from existing captures
- [ ] Identify command structure
- [ ] Map coordinate system
- [ ] Document drawing primitives
- [ ] Build rendering API

### Phase 5: Error Handling
- [ ] Trigger and capture error responses
- [ ] Document error codes
- [ ] Implement retry logic
- [ ] Implement reconnection handling

### Phase 6: SDK
- [ ] Create package structure
- [ ] Implement connection management
- [ ] Implement service base class
- [ ] Port teleprompter service
- [ ] Port dashboard service
- [ ] Add display service
- [ ] Add AI service (when ready)
- [ ] Add navigation service (when ready)
- [ ] Write documentation

### Phase 7: Testing
- [ ] Unit tests for protocol
- [ ] Integration tests
- [ ] Mock server for CI
- [ ] Documentation tests

---

## Timeline-Free Milestones

1. **Milestone: Capture Infrastructure** - BLE logging working, analysis tools ready
2. **Milestone: AI Protocol Complete** - Full AI request/response cycle documented and working
3. **Milestone: Navigation Protocol Complete** - Turn-by-turn display working
4. **Milestone: SDK Alpha** - Core services wrapped in clean API
5. **Milestone: SDK Beta** - Error handling, reconnection, all services
6. **Milestone: Production Ready** - Full test coverage, documentation, examples

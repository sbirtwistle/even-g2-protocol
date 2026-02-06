# Even AI Protocol

**Service ID**: 0x07 (Service) / 0x0720 (Request Flag)
**Status**: ✅ Working - Custom Q&A Confirmed
**Last Updated**: February 5, 2026

---

## Overview

Even AI is the G2's voice assistant feature. We have successfully reverse engineered the protocol to display **custom questions and answers** without the Even app or Even's cloud service.

## Flutter App Findings (Feb 2026)

Recent testing in the Flutter app uncovered a few operational requirements and signals:

- **Dual-arm connection required**: The official app requires both arms connected; we mirror this and see consistent voice flow only with both arms connected.
- **Right arm emits Even AI events**: Wake/exit events arrive from the right arm during voice interaction.
- **Response service IDs**: Even AI responses arrive on **0x0700** and **0x0701** (both observed).
- **CTRL ENTER on wake-up**: After a WAKE_UP event, the app must send **CTRL(ENTER)** to keep AI mode active and allow voice flow to proceed.

These changes enabled real-time voice interaction with the assistant (transcription + answers on glasses).

### Service IDs

| Service ID | Decimal | Flags | Direction | Purpose |
|------------|---------|-------|-----------|---------|
| `0x0700` | 1792 | 0x00 | ←GLASSES | Responses/ACKs from glasses |
| `0x0720` | 1824 | 0x20 | →GLASSES | Commands to glasses |

**Service**: 0x07 (Even AI)
**Flags**: Low byte indicates direction (0x00=response, 0x20=request)

---

## Working Protocol Flow

The **minimum working sequence** to display custom Q&A:

```
1. AUTH          - Standard 7-packet authentication
2. CTRL(ENTER)   - commandId=1, status=2 → Enter AI mode
3. ASK           - commandId=3 → Display question text
4. REPLY         - commandId=5 → Display answer text
```

**Key Discovery**: The `CTRL(ENTER)` command is **required** before ASK/REPLY will display. Without it, the glasses ignore AI commands.

**Voice Flow Note**: For live voice input, sending `CTRL(ENTER)` immediately after WAKE_UP keeps AI mode active and allows the phone to run speech recognition.

---

## Packet Format

### Query Packet (ASK) - 0x0720

```
Transport Header (8 bytes):
[AA] [21] [seq] [len] [01] [01] [07] [20]

Protobuf Payload:
08 03                - commandId: ASK (3)
10 XX                - magicRandom (request ID)
2a XX                - askInfo field
  14 08 00 10 00     - cmdCnt, streamEnable=0, textMode=0
  22 XX              - Length of text
  [UTF-8 text...]    - Query text

CRC (2 bytes):
[crc_lo] [crc_hi]
```

### Response Packet (REPLY) - 0x0700

```
Transport Header (8 bytes):
[AA] [12] [seq] [len] [01] [01] [07] [00]

Protobuf Payload:
08 05                - commandId: REPLY (5)
10 XX                - magicRandom
3a XX                - replyInfo field
  08 00              - streamEnable=0
  10 00              - textMode=0
  22 XX              - Length of text
  [UTF-8 text...]    - AI response text

CRC (2 bytes):
[crc_lo] [crc_hi]
```

---

## Example: "What's 10 + 10?"

Real capture showing query refinement and response:

### Query Evolution (0x0720)

**Packet 1 - Partial**
```
aa21241c01010720080310352a1408001000220e77686174277320313020706c7573fdaf

Service: 0x0720 (request)
commandId: 3 (ASK)
magicRandom: 53
askInfo.text: "what's 10 plus"
```

**Packet 2 - Refined**
```
aa21251c01010720080310362a1408001000220e776861742773203130202b203130a7ba

Service: 0x0720 (request)
commandId: 3 (ASK)
magicRandom: 54
askInfo.text: "what's 10 + 10"
```

**Packet 3 - Final**
```
aa21261d01010720080310372a1508001000220f576861742773203130202b2031303fc609

Service: 0x0720 (request)
commandId: 3 (ASK)
magicRandom: 55
askInfo.text: "What's 10 + 10?"
```

### AI Response (0x0700)

```
aa12c708010107000805103b3a00a8e4

Service: 0x0700 (response)
commandId: 5 (REPLY)
magicRandom: 59
replyInfo.text: "20"
```

---

## Protobuf Definitions

```protobuf
syntax = "proto3";

enum eEvenAICommandId {
    NONE_COMMAND = 0;
    CTRL = 1;
    VAD_INFO = 2;
    ASK = 3;
    ANALYSE = 4;
    REPLY = 5;
    SKILL = 6;
    PROMPT = 7;
    EVENT = 8;
    HEARTBEAT = 9;
    CONFIG = 10;
    COMM_RSP = 161;
}

enum eEvenAIStatus {
    STATUS_UNKNOWN = 0;
    EVEN_AI_WAKE_UP = 1;
    EVEN_AI_ENTER = 2;
    EVEN_AI_EXIT = 3;
}

enum eEvenAIVADStatus {
    VAD_STATUS_UNKNOWN = 0;
    VAD_START = 1;
    VAD_END = 2;
    VAD_TIMEOUT = 3;
}

message EvenAIAskInfo {
    int32 cmdCnt = 1;
    int32 streamEnable = 2;
    int32 textMode = 3;
    bytes text = 4;              // UTF-8 query text
    eErrorCode errorCode = 5;
}

message EvenAIReplyInfo {
    int32 cmdCnt = 1;
    int32 streamEnable = 2;
    int32 textMode = 3;
    bytes text = 4;              // UTF-8 response text
    eErrorCode errorCode = 5;
}

message EvenAIConfig {
    int32 voiceSwitch = 1;
    int32 streamSpeed = 2;       // Typically 32
    eErrorCode errorCode = 3;
}

message EvenAIVADInfo {
    eEvenAIVADStatus vadStatus = 1;
    eErrorCode errorCode = 2;
}

message EvenAIDataPackage {
    eEvenAICommandId commandId = 1;
    int32 magicRandom = 2;
    optional EvenAIControl ctrl = 3;
    optional EvenAIVADInfo vadInfo = 4;
    optional EvenAIAskInfo askInfo = 5;
    optional EvenAIReplyInfo replyInfo = 7;
    optional EvenAIConfig config = 13;
}
```

---

## Working Implementation

### Complete Python Example

```python
# Working sequence to display custom Q&A on Even AI card

def build_ctrl_enter(seq: int, magic: int) -> bytes:
    """CTRL command to enter AI mode - REQUIRED first!"""
    payload = bytes([
        0x08, 0x01,           # commandId = 1 (CTRL)
        0x10, magic,          # magicRandom
        0x1a, 0x02,           # ctrl field (field 3)
        0x08, 0x02            # status = 2 (EVEN_AI_ENTER)
    ])
    return build_packet(seq, 0x07, 0x20, payload)


def build_ask(seq: int, magic: int, text: str) -> bytes:
    """ASK command - displays question text"""
    text_bytes = text.encode('utf-8')

    askinfo = bytes([
        0x08, 0x00,           # cmdCnt = 0
        0x10, 0x00,           # streamEnable = 0
        0x18, 0x00,           # textMode = 0
        0x22,                 # text field
    ]) + encode_varint(len(text_bytes)) + text_bytes

    payload = bytes([
        0x08, 0x03,           # commandId = 3 (ASK)
        0x10, magic,          # magicRandom
        0x2a,                 # askInfo field (field 5)
    ]) + encode_varint(len(askinfo)) + askinfo

    return build_packet(seq, 0x07, 0x20, payload)


def build_reply(seq: int, magic: int, text: str) -> bytes:
    """REPLY command - displays answer text"""
    text_bytes = text.encode('utf-8')

    replyinfo = bytes([
        0x08, 0x00,           # cmdCnt = 0
        0x10, 0x00,           # streamEnable = 0
        0x18, 0x00,           # textMode = 0
        0x22,                 # text field
    ]) + encode_varint(len(text_bytes)) + text_bytes

    payload = bytes([
        0x08, 0x05,           # commandId = 5 (REPLY)
        0x10, magic,          # magicRandom
        0x3a,                 # replyInfo field (field 7)
    ]) + encode_varint(len(replyinfo)) + replyinfo

    return build_packet(seq, 0x07, 0x20, payload)


# Usage:
async def display_qa(client, question: str, answer: str):
    seq, magic = 8, 100

    # 1. Enter AI mode (REQUIRED!)
    await client.write_gatt_char(CHAR_WRITE, build_ctrl_enter(seq, magic))
    await asyncio.sleep(0.3)

    # 2. Display question
    await client.write_gatt_char(CHAR_WRITE, build_ask(seq+1, magic+1, question))
    await asyncio.sleep(1.0)

    # 3. Display answer
    await client.write_gatt_char(CHAR_WRITE, build_reply(seq+2, magic+2, answer))
```

### Verified Working Packets

**CTRL(ENTER)**:
```
aa21080a01010720080110641a0208025ca9
         ↑     ↑    ↑        ↑
        seq  svc  cmdId=1   status=2
```

**ASK "What is 2 + 2?"**:
```
aa21091e01010720080310652a16080010001800220e576861742069732032202b20323fc72b
                    ↑              ↑
                 cmdId=3        text bytes
```

**REPLY "The answer is 4!"**:
```
aa210a2001010720080510663a18080010001800221054686520616e737765722069732034218432
                    ↑              ↑
                 cmdId=5        text bytes
```

---

## Behavioral Notes

### Incremental Query Refinement

Like Conversate, Even AI uses **incremental updates**:
- Phone sends multiple ASK packets as speech is refined
- Each packet contains the **full query so far**
- Final packet is the most accurate transcription

**Why?** Real-time speech recognition improves over time.

### Voice Activation Detection (VAD)

Before ASK, the system uses VAD:
```
VAD_START: User starts speaking
VAD_END: User stops speaking
VAD_TIMEOUT: No speech detected
```

---

## Voice Input Implementation

### Architecture

The G2 glasses do **not** stream audio over BLE. Instead, voice input works as follows:

```
┌─────────────────────┐
│  G2 Glasses         │
│  (VAD Detection)    │
└──────────┬──────────┘
           │ BLE: VAD events
           ▼
┌─────────────────────┐
│  Phone              │
│  (Audio Recording)  │
│  (Speech-to-Text)   │
└──────────┬──────────┘
           │ BLE: ASK/REPLY
           ▼
┌─────────────────────┐
│  G2 Glasses         │
│  (Display Q&A)      │
└─────────────────────┘
```

### Voice Flow

1. **Wake**: User says "Hey Even" or long-presses temple
   - Glasses send `CTRL(status=1)` (WAKE_UP)

2. **VAD Start**: Glasses detect user speaking
   - Glasses send `VAD_INFO(vadStatus=1)` (VAD_START)
   - Phone begins audio recording + speech recognition

3. **VAD End**: Glasses detect silence
   - Glasses send `VAD_INFO(vadStatus=2)` (VAD_END)
   - Phone stops recording, finalizes transcription

4. **Query**: Phone sends transcribed text
   - Phone sends `ASK(text="user question")`
   - Phone queries LLM (Claude, GPT-4, etc.)

5. **Response**: Phone displays answer
   - Phone sends `REPLY(text="AI answer")`

### VAD Packet Format

VAD events come from the glasses on service `0x07-00`:

```
Transport Header (8 bytes):
[AA] [12] [seq] [len] [01] [01] [07] [00]

Protobuf Payload:
08 02                - commandId: VAD_INFO (2)
10 XX                - magicRandom
22 XX                - vadInfo field (field 4)
  08 XX              - vadStatus (1=START, 2=END, 3=TIMEOUT)

CRC (2 bytes):
[crc_lo] [crc_hi]
```

### CTRL Status Events

CTRL events indicate AI mode state changes:

| Status | Name    | Meaning               |
|--------|---------|-----------------------|
| 1      | WAKE_UP | "Hey Even" detected   |
| 2      | ENTER   | Entered AI mode       |
| 3      | EXIT    | Exited AI mode        |

### Phone-Side Speech Recognition

Since audio doesn't stream from glasses, the phone must:

1. Use its own microphone for audio capture
2. Perform speech-to-text locally or via cloud API
3. Send the transcribed text to glasses via ASK packet

**Recommended approach:**
- iOS: Native Speech framework
- Android: Android SpeechRecognizer
- Cross-platform: `speech_to_text` Flutter package

### Implementation Notes

- VAD events require glasses to be in AI mode
- Phone should start listening immediately on VAD_START
- Keep recording until VAD_END or timeout
- Incremental transcription updates are optional but improve UX

### Config Settings

Initial CONFIG packet sets:
```
voiceSwitch: 0 (off) or 1 (on)
streamSpeed: 32 (typical value)
```

---

## AI Skills

Even AI supports special commands via the SKILL message type:

```protobuf
enum eEvenAISkill {
    SKILL_NONE = 0;
    BRIGHTNESS = 1;
    TRANSLATE_CTRL = 2;
    NOTIFICATION = 3;
    TELEPROMPT = 4;
    NAVIGATE = 5;
    CONVERSATE = 6;
    QUICKLIST = 7;
    AUTO_BRIGHTNESS = 8;
}
```

These allow AI to control other G2 features:
- "Set brightness to 50%" → BRIGHTNESS skill
- "Show my notifications" → NOTIFICATION skill
- "Start navigation" → NAVIGATE skill

**Status**: Skill packets not yet captured in testing.



## Testing

### Test 1: Simple Math
- **Query**: "What's 10 + 10?"
- **Response**: "20"
- **Result**: ✅ Correct response

### Test 2: Incremental Refinement
- **Updates**: 3 progressive query packets
- **Timing**: ~500ms between updates
- **Result**: ✅ Smooth query refinement


## Future Work

### Multi-turn Conversations

Can we maintain context across multiple queries?
- "What's 10 + 10?" → "20"
- "Double that" → "40"?

**Status**: Not tested.

### Custom AI Backend

With this protocol, possible to:
- ✅ Send queries without Even app
- ✅ Use custom AI models (GPT, Claude, etc.)
- ✅ Build Even AI alternatives


## Credits

- **Protocol Discovery**: Soxi - January 2, 2026
- **Protobuf Definitions**: aegray (that parser is sweet!)

---

## Implementations

### Python

- [examples/even-ai/](../examples/even-ai/) - Direct Q&A display
- [examples/llm-teleprompter/](../examples/llm-teleprompter/) - LLM integration (OpenAI, Claude, Ollama)

### Flutter

- [flutter_app/](../flutter_app/) - Mobile app with AI Chat feature
  - Supports OpenRouter (Claude, GPT-4, Gemini, Llama)
  - Chat-style UI with conversation history
  - Secure API key storage

## See Also

- [Service IDs](services.md) - Complete service listing
- [Packet Structure](packet-structure.md) - Transport layer format

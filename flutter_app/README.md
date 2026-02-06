# Even G2 Teleprompter

A Flutter app for interfacing with Even Realities G2 smart glasses via BLE.

## Features

- **Teleprompter** - Display custom scrollable text on glasses
- **AI Chat** - Query LLM AI (Claude, GPT-4, etc.) and display Q&A on glasses
- **BLE Capture** - Research mode for BLE traffic analysis

## Quick Start

```bash
# Install dependencies
flutter pub get

# Run on connected device
flutter run
```

## Requirements

- Flutter SDK 3.7.2+
- iOS 12+ or Android 6.0+
- Even Realities G2 glasses
- OpenRouter API key (for AI Chat feature)

## Screens

### Home Screen

- Scan for G2 glasses via Bluetooth
- View discovered devices with signal strength
- Connect/disconnect from glasses
- Navigate to Teleprompter, AI Chat, or BLE Capture

### Teleprompter Screen

Display custom text on your glasses:
- Enter multi-line text
- Choose manual or AI auto-scroll mode
- Live progress indicator during send
- Text automatically formatted (25 chars/line, 10 lines/page)

### AI Chat Screen

Query AI and display Q&A on glasses:
- Chat-style conversation UI
- Supports multiple LLM providers via OpenRouter
- Questions displayed on glasses as you type
- AI responses displayed in native Even AI card format

**Supported Models:**
- Claude 3 Haiku (fast, recommended)
- Claude 3.5 Sonnet
- GPT-4o Mini
- GPT-4o
- Gemini Flash 1.5
- Llama 3.1 8B

### BLE Capture Screen

Research mode for protocol analysis:
- Real-time BLE packet capture
- Hex dump and parsed packet view
- Export to clipboard
- Filter by service type

## AI Chat Setup

1. Get an API key from [OpenRouter.ai](https://openrouter.ai)
2. Connect to your G2 glasses
3. Tap the brain icon (🧠) in the app bar
4. Tap Settings (⚙️) and enter your API key
5. Select your preferred model
6. Start asking questions!

## Architecture

```
lib/
├── core/
│   ├── constants/          # BLE UUIDs, protocol constants
│   └── utils/              # CRC, varint encoding, text formatting
├── data/
│   ├── models/             # Device, connection state, packets
│   ├── protocol/           # Packet builders (auth, teleprompter, even-ai)
│   ├── repositories/       # BLE repository abstraction
│   └── services/           # OpenRouter API client
├── domain/
│   └── services/           # Business logic (teleprompter, ai-chat)
└── presentation/
    ├── providers/          # Riverpod state management
    ├── screens/            # UI screens
    └── widgets/            # Reusable widgets
```

## Protocol Implementation

The app implements the following G2 protocols:

| Protocol | Service ID | Status |
|----------|------------|--------|
| Authentication | 0x80-00/20 | ✅ Working |
| Teleprompter | 0x06-20 | ✅ Working |
| Display Config | 0x0E-20 | ✅ Working |
| Even AI | 0x07-20 | ✅ Working |

## Dependencies

- **flutter_riverpod** - State management
- **flutter_blue_plus** - BLE communication
- **http** - OpenRouter API client
- **flutter_secure_storage** - Secure API key storage

## Related Documentation

- [Even AI Protocol](../docs/even-ai.md) - Protocol details
- [Teleprompter Protocol](../docs/teleprompter.md) - Protocol details
- [BLE Services](../docs/ble-uuids.md) - GATT services and characteristics

## Credits

- Azure OpenAI integration pattern from [flushpot1125/even-g2_PC](https://github.com/flushpot1125/even-g2_PC)
- Even AI protocol by Soxi
- Protocol research by the Even Realities community

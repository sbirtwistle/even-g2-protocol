# LLM Teleprompter

Query LLM AI providers and display Q&A on G2 glasses using the Even AI card.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your credentials

# Ask a question (uses OpenAI by default)
python llm_teleprompter.py "What is the capital of France?"

# Use different providers
python llm_teleprompter.py "Explain AI" --provider anthropic
python llm_teleprompter.py "Hello" --provider ollama

# Interactive mode (multiple questions)
python llm_teleprompter.py --interactive
```

## Supported Providers

| Provider | Flag | API Key Variable | Notes |
|----------|------|------------------|-------|
| OpenAI | `--provider openai` | `OPENAI_API_KEY` | Default. GPT-4o-mini recommended |
| Azure OpenAI | `--provider azure` | `AZURE_OPENAI_API_KEY` | Enterprise Azure deployments |
| Anthropic | `--provider anthropic` | `ANTHROPIC_API_KEY` | Claude models |
| Ollama | `--provider ollama` | (none) | Local models, requires Ollama running |

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
# OpenAI (default)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

# Azure OpenAI
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_KEY=your-key-here

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Ollama (no API key needed)
OLLAMA_MODEL=llama3.2
```

## Display Limits

The Even AI card has text limits:
- Question: ~150 bytes UTF-8
- Answer: ~200 bytes UTF-8

Longer responses are automatically truncated with "..."

## Interactive Mode

Use `--interactive` or `-i` for a conversation-like experience:

```bash
python llm_teleprompter.py -i

LLM Teleprompter - AI on G2 Glasses
==================================================
Provider: OpenAI (gpt-4o-mini)

Scanning for G2 glasses...
  Using: G2_R_XXXXX
  Connected!

Authenticating...
  Authenticated!

==================================================
Interactive mode. Type 'quit' to exit.
==================================================

You: What is 2+2?
  Entering AI mode...
  Question: What is 2+2?
  Querying OpenAI (gpt-4o-mini)...
  Answer: 2 + 2 equals 4.

You: quit
```

## Credits

- Azure OpenAI integration inspired by [flushpot1125/even-g2_PC](https://github.com/flushpot1125/even-g2_PC)
- Even AI protocol by Soxi

## See Also

- [Even AI Protocol](../../docs/even-ai.md) - Protocol documentation
- [examples/even-ai/](../even-ai/) - Direct Q&A display without LLM
- [examples/teleprompter/](../teleprompter/) - Long-form scrollable text

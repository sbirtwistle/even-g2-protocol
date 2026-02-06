"""
LLM Provider Abstractions

Supports multiple LLM backends:
- openai: OpenAI API (GPT-4, GPT-4o-mini)
- azure: Azure OpenAI Service
- anthropic: Anthropic Claude
- ollama: Local models via Ollama
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a query and return the response text."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI Service provider."""

    def __init__(self):
        from openai import AzureOpenAI
        endpoint = os.getenv("AZURE_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not endpoint or not api_key:
            raise ValueError("AZURE_ENDPOINT and AZURE_OPENAI_API_KEY must be set")
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-15-preview",
        )
        self.deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4")

    @property
    def name(self) -> str:
        return f"Azure OpenAI ({self.deployment})"

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self):
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    @property
    def name(self) -> str:
        return f"Claude ({self.model})"

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class OllamaProvider(LLMProvider):
    """Ollama local model provider."""

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        import ollama
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(model=self.model, messages=messages)
        return response["message"]["content"]


def get_provider(name: str) -> LLMProvider:
    """Factory function to get provider by name."""
    providers = {
        "openai": OpenAIProvider,
        "azure": AzureOpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown provider: {name}. Options: {list(providers.keys())}")
    return providers[name]()

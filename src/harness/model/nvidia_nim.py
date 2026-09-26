"""NVIDIA NIM model provider implementation."""

from harness.model.client import NvidiaNimClient
from harness.model.provider import ModelProvider


class NvidiaNimProvider(NvidiaNimClient, ModelProvider):
    """Provider implementation for NVIDIA NIM API (OpenAI-compatible)."""

    pass

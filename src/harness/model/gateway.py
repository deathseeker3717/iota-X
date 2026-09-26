"""Model Gateway: High-level client for model inference."""

import os
from typing import Any, Dict, List, Optional, Union

from harness.model.nvidia_nim import NvidiaNimProvider
from harness.model.provider import ModelProvider
from harness.model.schemas import Message, ModelRequest, ModelResponse, ToolDefinition


class ModelGateway:
    """Gateway separating agents from specific model providers.
    
    Agents communicate exclusively with ModelGateway without knowing
    the underlying provider implementation (e.g. NVIDIA NIM vs evaluation model).
    """

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> "ModelGateway":
        """Instantiate ModelGateway from a configuration dictionary."""
        model_cfg = config.get("model", {})
        provider_name = model_cfg.get("provider", "nvidia_nim")
        model_name = model_cfg.get("model_name", "meta/llama-3.1-70b-instruct")

        if provider_name == "nvidia_nim":
            base_url = model_cfg.get("base_url", "https://integrate.api.nvidia.com/v1")
            provider = NvidiaNimProvider(
                model_name=model_name,
                api_key=api_key or os.getenv("AI_API_KEY"),
                base_url=base_url,
            )
            return cls(provider=provider)
        else:
            raise ValueError(f"Unsupported model provider: '{provider_name}'")

    def generate(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **extra_params: Any,
    ) -> ModelResponse:
        """High-level generate API consumed by agents."""
        normalized_messages: List[Message] = []
        for msg in messages:
            if isinstance(msg, Message):
                normalized_messages.append(msg)
            elif isinstance(msg, dict):
                normalized_messages.append(Message(role=msg["role"], content=msg["content"]))
            else:
                raise TypeError(f"Invalid message type: {type(msg)}")

        request = ModelRequest(
            messages=normalized_messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
        )
        return self.provider.generate(request)

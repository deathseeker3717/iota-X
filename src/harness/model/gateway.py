"""Model Gateway: High-level client for model inference."""

import json
import os
import re
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from harness.model.client import NvidiaNimClient
from harness.model.interface import ModelInterface
from harness.model.nvidia_nim import NvidiaNimProvider
from harness.model.ollama import OllamaClient, OllamaProvider
from harness.model.provider import ModelProvider
from harness.model.schemas import Message, ModelRequest, ModelResponse, ToolDefinition

T = TypeVar("T")


class ModelGateway:
    """Gateway separating agents from specific model providers.
    
    Agents communicate exclusively with ModelGateway without knowing
    the underlying provider implementation (e.g. NVIDIA NIM vs Ollama vs evaluation model).
    They simply call model.generate(...) or model.generate_structured(...).
    """

    def __init__(self, provider: ModelInterface, backup_provider: Optional[ModelInterface] = None) -> None:
        self.provider = provider
        self.backup_provider = backup_provider

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> "ModelGateway":
        """Instantiate ModelGateway from a configuration dictionary."""
        
        def create_provider(provider_name: str, model_cfg: Dict[str, Any]) -> ModelInterface:
            if provider_name == "mock":
                from harness.model.mock import MockProvider
                should_fail = model_cfg.get("mock_fail", False)
                return MockProvider(should_fail=should_fail)
            elif provider_name in ("nvidia_nim", "nim", "default"):
                model_name = model_cfg.get("model_name", "meta/llama-3.1-70b-instruct")
                base_url = model_cfg.get("base_url", "https://integrate.api.nvidia.com/v1")
                return NvidiaNimProvider(
                    model_name=model_name,
                    api_key=api_key or os.getenv("AI_API_KEY"),
                    base_url=base_url,
                )
            elif provider_name in ("ollama", "local"):
                model_name = model_cfg.get("model_name", "gpt-oss:20b")
                base_url = model_cfg.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"))
                timeout = float(model_cfg.get("timeout", os.getenv("OLLAMA_TIMEOUT", "300.0")))
                return OllamaProvider(
                    model_name=model_name,
                    base_url=base_url,
                    timeout=timeout,
                )
            else:
                raise ValueError(f"Unsupported model provider: '{provider_name}'")

        model_cfg = config.get("model", {})
        provider_name = model_cfg.get("provider", os.getenv("MODEL_PROVIDER", "nvidia_nim")).lower()
        primary_provider = create_provider(provider_name, model_cfg)
        
        backup_provider = None
        fallback_name = model_cfg.get("fallback_provider", os.getenv("MODEL_FALLBACK_PROVIDER"))
        if fallback_name:
            # Re-use config but override provider name
            backup_provider = create_provider(fallback_name.lower(), model_cfg)
            
        return cls(provider=primary_provider, backup_provider=backup_provider)

    def generate(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **extra_params: Any,
    ) -> ModelResponse:
        """High-level generate API consumed by agents."""
        normalized_messages: List[Message] = []
        for msg in messages:
            if isinstance(msg, Message):
                normalized_messages.append(msg)
            elif isinstance(msg, dict):
                normalized_messages.append(
                    Message(
                        role=msg["role"],
                        content=msg["content"],
                        name=msg.get("name"),
                        tool_call_id=msg.get("tool_call_id"),
                    )
                )
            else:
                raise TypeError(f"Invalid message type: {type(msg)}")

        request = ModelRequest(
            messages=normalized_messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            extra_params=extra_params,
        )
        import logging
        logger = logging.getLogger(__name__)

        try:
            return self.provider.generate(request)
        except Exception as e:
            if self.backup_provider:
                logger.warning(f"Primary provider failed: {e}. Trying fallback provider.")
                return self.backup_provider.generate(request)
            else:
                logger.error(f"Primary provider failed and no fallback configured: {e}")
                raise e
    def generate_structured(
        self,
        messages: Union[List[Message], List[Dict[str, str]]],
        schema_cls: Optional[Type[T]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **extra_params: Any,
    ) -> Dict[str, Any]:
        """Generate structured output parsed as a dictionary or target class.
        
        Extracts JSON from response content (handling markdown code blocks if present).
        If schema_cls has a `from_dict` method, returns an instance of schema_cls.
        Otherwise returns the parsed dictionary.
        """
        response = self.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra_params,
        )

        content = response.content or ""
        parsed_dict = self.extract_json(content)

        if schema_cls and hasattr(schema_cls, "from_dict"):
            try:
                return getattr(schema_cls, "from_dict")(parsed_dict)
            except Exception as e:
                # Fallback instantiation or dict return
                return parsed_dict

        return parsed_dict

    @staticmethod
    def extract_json(content: str) -> Dict[str, Any]:
        """Extract and parse JSON object from text content."""
        content_stripped = content.strip()

        # Strip reasoning/thought tags if present (e.g., <think>...</think>)
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", content_stripped, flags=re.DOTALL).strip()
        target = cleaned if cleaned else content_stripped

        # Try direct JSON parsing
        try:
            return json.loads(target)
        except json.JSONDecodeError:
            pass

        # Try extracting ```json ... ``` block
        json_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", target, re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try searching for first '{' and last '}'
        start = target.find("{")
        end = target.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(target[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {"raw_text": content}

"""NVIDIA NIM Client implementation."""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from harness.model.interface import ModelInterface
from harness.model.schemas import Message, ModelRequest, ModelResponse, ToolCall


class NvidiaNimClient(ModelInterface):
    """Client implementation for NVIDIA NIM API (OpenAI-compatible)."""

    def __init__(
        self,
        model_name: str = "meta/llama-3.1-70b-instruct",
        api_key: Optional[str] = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout: float = 60.0,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.getenv("AI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Send chat completion request to NVIDIA NIM API."""
        if not self.api_key:
            raise ValueError(
                "AI_API_KEY environment variable is not set and no API key was provided."
            )

        endpoint = f"{self.base_url}/chat/completions"
        payload = self._build_payload(request)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                response_json = json.loads(body)
                return self._parse_response(response_json)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"NVIDIA NIM API request failed with status {e.code}: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to connect to NVIDIA NIM API: {e.reason}") from e

    def _build_payload(self, request: ModelRequest) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        for msg in request.messages:
            msg_dict: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.tools:
            payload["tools"] = [tool.to_dict() for tool in request.tools]

        if request.response_format:
            payload["response_format"] = request.response_format

        if request.extra_params:
            payload.update(request.extra_params)

        return payload

    def _parse_response(self, response_json: Dict[str, Any]) -> ModelResponse:
        choices = response_json.get("choices", [])
        if not choices:
            return ModelResponse(raw_response=response_json)

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content")
        finish_reason = first_choice.get("finish_reason")

        tool_calls: Optional[List[ToolCall]] = None
        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls:
            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {"raw": args_str}

                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=func.get("name", ""),
                        arguments=args,
                    )
                )

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=response_json,
            finish_reason=finish_reason,
        )

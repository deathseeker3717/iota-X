"""Unit and integration tests for OllamaClient and OllamaProvider."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from harness.model import (
    Message,
    ModelGateway,
    ModelRequest,
    ModelResponse,
    OllamaClient,
    OllamaProvider,
    ToolCall,
    ToolDefinition,
)


def test_ollama_client_defaults():
    client = OllamaClient()
    assert client.model_name == "gpt-oss:20b"
    assert client.base_url == "http://localhost:11434/v1"


def test_ollama_client_custom_config():
    client = OllamaClient(
        model_name="gpt-oss:20b",
        base_url="http://127.0.0.1:11434/v1/",
    )
    assert client.model_name == "gpt-oss:20b"
    assert client.base_url == "http://127.0.0.1:11434/v1"


@patch("urllib.request.urlopen")
def test_ollama_client_generate_mocked(mock_urlopen):
    mock_payload = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Hello from gpt-oss:20b via Ollama!",
                    "tool_calls": [
                        {
                            "id": "call_ollama_1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "main.py"}',
                            },
                        }
                    ],
                },
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    client = OllamaClient(model_name="gpt-oss:20b")
    request = ModelRequest(
        system_prompt="You are a helpful coding assistant.",
        messages=[Message(role="user", content="Hello")],
        tools=[
            ToolDefinition(
                name="read_file",
                description="Read file contents",
                parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            )
        ],
        temperature=0.3,
    )

    response = client.generate(request)

    assert isinstance(response, ModelResponse)
    assert response.content == "Hello from gpt-oss:20b via Ollama!"
    assert response.finish_reason == "stop"
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {"path": "main.py"}

    # Verify request payload sent over urllib
    req_args = mock_urlopen.call_args[0][0]
    sent_payload = json.loads(req_args.data.decode("utf-8"))
    assert sent_payload["model"] == "gpt-oss:20b"
    assert sent_payload["messages"][0] == {"role": "system", "content": "You are a helpful coding assistant."}
    assert sent_payload["messages"][1] == {"role": "user", "content": "Hello"}
    assert sent_payload["stream"] is False
    assert sent_payload["temperature"] == 0.3


def test_gateway_from_config_ollama():
    config = {
        "model": {
            "provider": "ollama",
            "model_name": "gpt-oss:20b",
            "base_url": "http://localhost:11434/v1",
        }
    }
    gateway = ModelGateway.from_config(config)
    assert isinstance(gateway.provider, OllamaProvider)
    assert gateway.provider.model_name == "gpt-oss:20b"
    assert gateway.provider.base_url == "http://localhost:11434/v1"


@pytest.mark.skipif(
    not os.getenv("ENABLE_OLLAMA_INTEGRATION_TESTS"),
    reason="Ollama integration test disabled. Set ENABLE_OLLAMA_INTEGRATION_TESTS=1 to run.",
)
def test_ollama_live_integration():
    """Live integration test against Ollama gpt-oss:20b instance."""
    gateway = ModelGateway.from_config({"model": {"provider": "ollama", "model_name": "gpt-oss:20b"}})
    response = gateway.generate(
        messages=[{"role": "user", "content": "Return the single word 'OK'."}],
        system_prompt="You are a precise assistant.",
        temperature=0.0,
    )
    assert response.content is not None
    assert len(response.content.strip()) > 0

#!/usr/bin/env python3
"""Manual verification script for Ollama gpt-oss:20b integration.

Flow: Python → ModelInterface → OllamaClient → gpt-oss:20b → ModelResponse

Usage:
    python scripts/verify_ollama.py
"""

import sys
from harness.model import Message, ModelGateway, ModelRequest, OllamaClient


def main() -> None:
    print("==================================================")
    print("Verifying: Python -> ModelInterface -> Ollama -> gpt-oss:20b")
    print("==================================================")

    # 1. Instantiate OllamaClient implementing ModelInterface
    client = OllamaClient(
        model_name="gpt-oss:20b",
        base_url="http://localhost:11434/v1",
    )

    # 2. Wrap in ModelGateway
    gateway = ModelGateway(provider=client)

    # 3. Create ModelRequest / messages
    prompt = "Write a python function to add two numbers."
    print(f"\n[Request Prompt]: {prompt}")

    try:
        response = gateway.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert Python engineer.",
            temperature=0.2,
        )

        print("\n[Response received from gpt-oss:20b]:")
        print(response.content)

        if response.tool_calls:
            print(f"\n[Tool Calls]: {response.tool_calls}")

        print("\n[Status]: Verification Successful!")
    except Exception as e:
        print(f"\n[Error connecting to Ollama]: {e}")
        print("Note: Ensure Ollama is running (`ollama serve`) and model 'gpt-oss:20b' is pulled (`ollama pull gpt-oss:20b`).")
        sys.exit(1)


if __name__ == "__main__":
    main()

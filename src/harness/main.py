"""Main entry point for the AI Coding Harness."""

import os
import sys


def main() -> None:
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("Warning: AI_API_KEY environment variable is not set.", file=sys.stderr)
    print("AI Coding Harness initialized.")


if __name__ == "__main__":
    main()

# AI Coding Harness (Hackathon 2026)

## Purpose

The **AI Coding Harness** is an orchestrated coding platform designed around a foundation model. Rather than relying on a loose federation of independent, conversational AI agents, this harness builds a single centralized, deterministically controlled system to solve complex coding tasks, research repositories, implement modifications, and verify correctness.

## High-Level Architecture

The system operates under a single **Central Orchestrator** managing specialized agent roles, state transitions, tool execution, and context.

```
Central Orchestrator
    |
    +-- Planner Agent
    +-- Repository Research Agent
    +-- Coding Agent
    +-- Verification Agent
    +-- Recovery Agent
    |
    +-- Shared Tool Layer
    +-- Context Manager
    +-- Repository Intelligence
    +-- Model Abstraction Layer
    +-- Open-source Agent Adapters
```

### Core Architectural Principles

- **Single Orchestrated Harness**: One unified harness controlling execution rather than autonomous uncoordinated agents.
- **Orchestrator Ownership**: The Central Orchestrator strictly owns:
  - Task state
  - Agent routing
  - Execution flow
  - Iteration limits
  - Context selection
  - Failure recovery
- **Structured Communication**: Agents communicate via structured state schemas rather than uncontrolled natural-language conversations.

## Project Structure

```
ai-coding-harness/
│
├── Makefile
├── README.md
├── .gitignore
├── .env.example
├── pyproject.toml
│
├── src/
│   └── harness/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── orchestrator/
│       ├── agents/
│       ├── model/
│       ├── context/
│       ├── tools/
│       ├── repository/
│       ├── verification/
│       └── adapters/
│
├── tests/
│
└── configs/
    └── config.yaml
```

## Getting Started

### Prerequisites

- Python 3.10+
- An API key for your foundation model

### Setup

Copy `.env.example` to `.env` and set your key:
```bash
cp .env.example .env
```

Install the project:
```bash
make setup
```

### Usage

Run the harness:
```bash
make run
```

Run tests:
```bash
make test
```

Clean build and cache artifacts:
```bash
make clean
```

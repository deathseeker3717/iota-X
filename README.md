# AI Coding Harness (Hackathon 2026)

## Purpose

The **AI Coding Harness** is an orchestrated coding platform designed around a foundation model. Rather than relying on a loose federation of independent, conversational AI agents, this harness builds a single centralized, deterministically controlled system to solve complex coding tasks, research repositories, implement modifications, and verify correctness.

## High-Level Architecture

The system operates under a single **Central Orchestrator** managing specialized agent roles, state transitions, tool execution, and context.

```
Central Orchestrator (Aditya)
    |
    +-- AI Brain / Model & Agents (Shaurya)
    |     +-- Model Gateway & NIM
    |     +-- Planner, Coder, Critic
    |
    +-- AI Hands / Tools & Repository (Arnav)
    |     +-- Search, File Ops, Shell Exec
    |     +-- Repository Intelligence
    |
    +-- AI Memory & Observability (Aryan)
          +-- Context Manager & Selector
          +-- Multi-Tier Memory (Short-Term, Task, Repo)
          +-- Context Compressor & Fact Extractor
          +-- Execution Tracer & ASCII Trace
          +-- Metrics & Token / Cost Tracker
          +-- Agent Trajectory & Diagnostics
          +-- EventBus Pub/Sub
```

### Core Architectural Principles

- **Single Orchestrated Harness**: One unified harness controlling execution rather than autonomous uncoordinated agents.
- **Orchestrator Ownership**: The Central Orchestrator strictly owns:
  - Task state
  - Agent routing
  - Execution flow
  - Iteration limits
  - Context selection & Memory
  - Observability & Tracing
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
│       │   ├── orchestrator.py
│       │   ├── router.py
│       │   ├── state.py
│       │   └── workflow.py
│       │
│       ├── context/
│       │   ├── manager.py
│       │   ├── memory.py
│       │   ├── compressor.py
│       │   └── selector.py
│       │
│       ├── observability/
│       │   ├── tracer.py
│       │   ├── events.py
│       │   ├── metrics.py
│       │   └── logger.py
│       │
│       ├── model/
│       ├── agents/
│       ├── tools/
│       ├── repository/
│       ├── verification/
│       └── adapters/
│
├── tests/
│   ├── test_context_manager.py
│   ├── test_observability.py
│   ├── test_orchestrator.py
│   ├── test_orchestrator_integration.py
│   └── test_model_gateway.py
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

# 🚀 Iota Code (AI Coding Harness)

Welcome to **Iota Code**, the next-generation AI-powered IDE built on top of the Code-OSS (VS Code) foundation, seamlessly integrated with a powerful, deterministic Agentic AI backend (the **AI Coding Harness**).

Unlike standard chat extensions that rely on unpredictable prompts, Iota Code uses a **Centralized Orchestrator** to control specialized agents (Planner, Researcher, Coder, Verifier) in a tightly bound execution loop. It researches your repository, writes code, tests the code, auto-recovers from failures, and seamlessly streams the results directly into your IDE.

---

## 🏗️ High-Level Architecture

The system operates across two main components:

1. **Iota Code Frontend**: A fully branded, standalone desktop application (forked from Code-OSS) containing the bespoke AI Chat Extension.
2. **AI Harness Backend**: A FastAPI server that runs locally, securely holding your API keys, orchestrating the Agents, providing File/Terminal Tools, and communicating with Foundation Models (NVIDIA NIM, Ollama, etc.).

```text
       IOTA CODE IDE (Frontend)
                  │
          HTTP / SSE Stream
                  │
                  ▼
        HARNESS SERVER (Backend)
                  │
          Central Orchestrator
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
  AI Brain     AI Hands   AI Memory
 (Agents &    (Tools &    (Context &
  Models)       Git)       Events)
```

---

## 🚀 Getting Started

To experience Iota Code, you need to start the Backend Server, and then launch the Frontend IDE.

### Step 1: Start the Backend Server (Mac & Windows)

The backend handles all AI logic and secure API key management. 

**Prerequisites:**
- Python 3.10+
- An AI API key (e.g., NVIDIA NIM)

**1. Clone and Setup Environment:**
```bash
# Set up the virtual environment and install dependencies
make setup
```

**2. Configure API Keys:**
```bash
# Copy the example environment file
cp .env.example .env
```
Open the `.env` file and securely add your API key (e.g., `AI_API_KEY=nvapi-...`). The frontend never sees this key!

**3. Run the Server:**
```bash
# Starts the FastAPI/SSE server on http://127.0.0.1:8000
make run
```
*You can also run `make test` to execute the automated test suite without consuming API tokens.*

---

### Step 2: Launch the Iota Code IDE (Frontend)

With the backend running, you can now launch the branded Iota Code desktop application. We provide convenient launch scripts for both Mac and Windows.

#### 🍎 For macOS Users
You can launch the IDE directly using the provided shell script:
```bash
./scripts/run_iota_code.sh
```
*Alternatively, you can package it into a distributable standalone `.dmg` file using `./scripts/package_mac_dmg.sh`.*

#### 🪟 For Windows Users
You can launch the IDE using the provided Batch or PowerShell scripts:
```cmd
.\scripts\run_iota_code.bat
```
*or using PowerShell:*
```powershell
.\scripts\run_iota_code.ps1
```

---

## 🧠 Using Iota Code

Once the IDE opens, navigate to the **Iota Code AI Chat** panel on the sidebar.

You can ask the AI to:
- **"Explain the architecture of this repository."** *(It will use Repository Intelligence tools to search your local files).*
- **"Create a file called hello.py with a function hello(name) that returns a greeting, and write tests for it."** *(It will plan, code, execute terminal tests, and auto-fix any failures before responding!)*

---

## ⚙️ Project Structure

```text
ai-coding-harness/
│
├── Makefile                  # Build & Run commands
├── .env.example              # Safe API Key templates
│
├── src/harness/              # BACKEND: AI Agent Orchestrator
│   ├── adapters/http/        # FastAPI Server & SSE Streams
│   ├── orchestrator/         # State Machine & Agent Router
│   ├── context/              # Multi-tier Memory
│   ├── model/                # API Gateway (NVIDIA, Mock, Ollama)
│   ├── tools/                # File & Shell Execution
│   └── verification/         # Test runner & Auto-Recovery
│
├── editor/                   # FRONTEND: Iota Code (Code-OSS)
│   └── code-oss-extension/   # Iota Code React/Webview UI
│
├── scripts/                  # Launch scripts for Mac & Win
└── tests/                    # Pytest suite
```

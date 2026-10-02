# 🔍 PeerLens — Multi-Agent AI Research Paper Reviewer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vitejs.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)

**PeerLens** is an advanced, multi-agent AI system designed to conduct rigorous, structured peer reviews of academic research papers. Built on LangGraph and Google Gemini, PeerLens orchestrates specialized evaluation agents to critique methodology, mathematical rigor, novelty, clarity, and structural claims.

---

## ✨ Features

- **Multi-Agent Review Pipeline**:
  - **🔬 Rigor Agent**: Scrutinizes mathematical validity, experimental methodology, baseline fairness, and empirical justifications.
  - **📖 Clarity Agent**: Evaluates structural flow, exposition, section completeness, terminology, and readability.
  - **🚀 Novelty Agent & Agentic RAG**: Validates original contributions and runs automated literature lookups via ArXiv to flag uncited prior art.
  - **⚖️ Meta-Reviewer**: Synthesizes scores, aggregates feedback, computes confidence-weighted recommendations, and generates an actionable summary.
- **Human-in-the-Loop & Reconsideration**:
  - Authors can dispute or rebut specific critique points.
  - An intelligent **Reconsideration Agent** objectively re-evaluates reviewer findings against author rebuttals.
- **Revision Tracking & Differential Analysis**:
  - Upload revised manuscripts (v1 vs v2+) to verify whether previously raised issues have been resolved.
- **Interactive UI**:
  - Built with React 19, TypeScript, Tailwind CSS, and Framer Motion.
  - Real-time review status updates, granular scorecards, and interactive dispute resolution.

---

## 🏗️ Architecture

```
peerlens/
├── backend/
│   ├── agents/          # Specialized review & rebuttal agents
│   ├── graph/           # LangGraph workflow definition & state machine
│   ├── models/          # Model providers (Gemini, fallback adapters)
│   ├── prompts/         # Curated system prompts for peer review personas
│   ├── rag/             # Paper vectorization & ArXiv literature retrieval
│   ├── schemas/         # Pydantic schemas for structured outputs
│   ├── tests/           # Comprehensive pytest suite
│   ├── tools/           # PDF parsers, ArXiv tools, and utilities
│   ├── database.py      # SQLite persistence layer for papers & reviews
│   ├── main.py          # FastAPI application & REST endpoints
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/             # React application (components, state, types)
│   ├── package.json     # Node.js dependencies & scripts
│   └── vite.config.ts   # Vite configuration
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher
- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)

---

### 1. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - On Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - On Linux/macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the `backend/` directory (or copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Add your API keys:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key
   GOOGLE_API_KEY=your_actual_gemini_api_key
   ```

5. **Start the FastAPI backend server**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The backend API will be available at `http://localhost:8000`. You can explore interactive Swagger docs at `http://localhost:8000/docs`.

---

### 2. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   Create a `.env` file in the `frontend/` directory (or copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Ensure the API URL points to the backend:
   ```env
   VITE_API_URL=http://localhost:8000
   ```

4. **Start the Vite development server**:
   ```bash
   npm run dev
   ```
   Open your browser and navigate to `http://localhost:3000`.

---

## 🧪 Running Tests

To run the backend test suite:
```bash
cd backend
pytest tests/ -v
```

To run frontend type checks:
```bash
cd frontend
npm run lint
```

---

## 📄 Supported Document Formats
- PDF (`.pdf`)
- Markdown (`.md`)
- Plain Text (`.txt`)

---

## 🔒 Security & Privacy
- API keys and environment variables are strictly excluded from version control.
- Never commit `.env` or database files (`*.db`, `*.sqlite`). Always reference `.env.example`.

---

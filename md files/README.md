# AI Autonomous Test Generation & Execution Platform

> 🤖 Upload your project → AI understands your code → Generates tests → Executes them

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python -m venv myvenv
myvenv\Scripts\activate     # Windows
# source myvenv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env and fill in your values
copy .env.example .env
# Edit .env with your GROQ_API_KEY (free at https://console.groq.com)
```

### 3. Run the Server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload/zip` | Upload a ZIP file |
| `POST` | `/api/v1/upload/github` | Submit a GitHub URL |
| `GET` | `/api/v1/projects/` | List all projects |
| `GET` | `/api/v1/projects/{id}` | Get project details |
| `DELETE`| `/api/v1/projects/{id}` | Delete a project |
| `POST` | `/api/v1/tests/generate/{id}` | Generate tests |
| `GET` | `/api/v1/tests/{id}` | List generated tests |
| `POST` | `/api/v1/tests/execute/{id}` | Execute tests |
| `GET` | `/api/v1/results/{id}` | Get test results |

## 🏗️ Architecture

```
Upload → Ingestion → AST Parsing → AI Agents (CrewAI) → Test Generation → pytest Execution → Results
```

See the full architecture document in the project artifacts for detailed diagrams.

## 📦 Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async)
- **AI Engine**: CrewAI + LangChain + Groq (Llama 3.3)
- **Code Parsing**: Python AST + tree-sitter
- **Test Execution**: pytest (sandboxed)
- **Task Queue**: Celery + Redis
- **Database**: SQLite (dev) / PostgreSQL (prod)

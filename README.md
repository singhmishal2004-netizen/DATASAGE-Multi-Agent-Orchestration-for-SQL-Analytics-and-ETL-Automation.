<h1 align="center">DataSage</h1>
<p align="center"><strong>Multi-agent orchestration for SQL analytics and ETL automation</strong></p>
<p align="center">
  Ask questions about your data. Run guarded SQL analytics. Extract and transform API data, all through one conversational interface.
</p>

DataSage is an agentic data assistant built with **LangGraph, LangChain, FastAPI, Streamlit and PostgreSQL**. It takes natural-language requests and routes each one to a specialist: a **SQL Analyst** for read-only database analytics, or an **ETL Analyst** for API extraction and controlled data transformation.

The goal was not just to connect an LLM to a database, but to combine agent orchestration, tool execution, validation, database context, a usable UI and a cloud deployment in one end-to-end application.

---

## Contents

1. [Features](#1-features)
2. [Live application](#2-live-application)
3. [Architecture](#3-architecture)
4. [Agent workflows](#4-agent-workflows)
5. [Safety and validation](#5-safety-and-validation)
6. [Tech stack](#6-tech-stack)
7. [Project structure](#7-project-structure)
8. [Database and sample data](#8-database-and-sample-data)
9. [Run locally](#9-run-locally)
10. [API reference](#10-api-reference)
11. [Example requests](#11-example-requests)
12. [Deployment](#12-deployment)
13. [Engineering decisions](#13-engineering-decisions)
14. [Limitations and roadmap](#14-limitations-and-roadmap)
15. [Author](#15-author)

---

## 1. Features

| Capability | What you can ask | What happens |
|---|---|---|
| **SQL analytics** | Questions about users, rides, vehicles, payments, ratings | Gathers schema context, generates SQL, validates it, executes it, explains the result |
| **API extraction** | Pull data from a public JSON API | Calls the extraction tool and saves records as CSV, JSON or Parquet |
| **Data transformation** | Clean, select, rename, sort or reshape a dataset | Builds a structured plan, validates it, applies allowlisted Pandas operations |
| **File download** | Fetch generated CSV output | Frontend requests the file from the backend download endpoint |

**Design principles**

- **Specialised agents:** routing, SQL analysis and ETL work have separate responsibilities.
- **Schema-aware SQL:** the SQL agent reads the database structure before writing a query.
- **Validate before execute:** generated SQL and ETL plans pass application-level checks first.
- **Tools do the work:** agents select tools; Python utilities and the database carry out operations.
- **Separate frontend and backend:** Streamlit for the UX, FastAPI for the API.

---

## 2. Live application

| Component | Host |
|---|---|
| Frontend | Streamlit Community Cloud |
| Backend | Render Web Service |
| Database | Neon PostgreSQL |

- API health: <https://datasage-multi-agent-orchestration-for.onrender.com/health>
- API docs: <https://datasage-multi-agent-orchestration-for.onrender.com/docs>

<!-- Add your Streamlit Community Cloud app URL here once you want it displayed publicly. -->

---

## 3. Architecture

```mermaid
flowchart TD
    U[User] --> UI[Streamlit Frontend]
    UI --> API[FastAPI Backend]
    API --> DA[Data Agent - LangGraph Router]

    DA -->|SQL request| SQL[SQL Analyst Agent]
    DA -->|ETL request| ETL[ETL Analyst Agent]

    SQL --> SCHEMA[Database Schema Context]
    SQL --> GUARD[SQL Guard - SQLGlot validation]
    GUARD --> DB[(Neon PostgreSQL)]
    DB --> SQL

    ETL --> ETOOLS[ETL Tools]
    ETOOLS --> APIEXT[External JSON API]
    ETOOLS --> PLAN[Validated Pandas Transformation Plan]
    PLAN --> FILES[CSV / JSON / Parquet files]

    SQL --> DA
    ETL --> DA
    DA --> API
    API --> UI
```

**LangGraph agent graphs**

<table align="center">
  <tr>
    <th align="center">Data Agent (router)</th>
    <th align="center">SQL Analyst</th>
    <th align="center">ETL Analyst</th>
  </tr>
  <tr>
    <td align="center" valign="top"><img src="data_agent_graph.png" alt="Data Agent graph" height="320"></td>
    <td align="center" valign="top"><img src="sql_agent_graph.png" alt="SQL Analyst graph" height="320"></td>
    <td align="center" valign="top"><img src="etl_analyst_graph.png" alt="ETL Analyst graph" height="320"></td>
  </tr>
</table>

---

## 4. Agent workflows

### 4.1 Data Agent (routing)

`Agents/data_agent.py` is the entry point. It reads the user's message and delegates:

- SQL-oriented requests go to the **SQL Analyst**.
- Extraction or transformation requests go to the **ETL Analyst**.
- The chosen agent's result is returned through the graph.

### 4.2 SQL Analyst (database analytics)

`Agents/sql_analyst.py`

1. Understand and refine the question.
2. Retrieve relevant schema information from PostgreSQL.
3. Build a prompt with the question and schema context.
4. Generate the SQL query.
5. Validate it with the SQL guard.
6. Execute the accepted query.
7. Return a human-readable answer.

### 4.3 ETL Analyst (extraction and transformation)

`Agents/etl_analyst.py`, using tools from `utils/etl_tools.py`

**Extraction**

1. The user supplies an API URL, output folder and format.
2. The agent selects `extract_load_tool`.
3. The tool fetches the JSON response and Pandas normalises it into a table.
4. The dataset is saved as CSV, JSON or Parquet.

**Transformation**

1. The user names an input file and describes the changes.
2. The agent reads a small preview of the dataset.
3. The LLM produces a structured transformation plan.
4. The plan is validated, then the ETL utility applies it.
5. The result is saved in the requested format.

**Supported operations:** remove duplicate rows, drop rows with nulls in selected columns, fill nulls in a column, rename columns, select columns, sort values.

```text
data/
├── extract/    extracted_data.csv
└── transform/  transformed_data.csv
```

---

## 5. Safety and validation

LLM output is treated as untrusted. Validation sits between the model and execution.

| Guard | File | What it does |
|---|---|---|
| **SQL guard** | `Guardrails/sql_guard.py` | Uses SQLGlot to inspect generated SQL. Built for read-only analytics; blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` and similar. |
| **ETL guard** | `Guardrails/etl_guard.py` | Validates transformation plans, restricts file access to the project data directory, and checks output formats. Only allowlisted operations run; no arbitrary LLM-generated Python. |

> **Note:** these are application-level safeguards, not a guarantee of security. Before exposing the service to untrusted users, add authentication and authorisation, rate limiting, SSRF protection for extraction URLs, resource limits and least-privilege database permissions. Protect the download endpoint if files are private.

---

## 6. Tech stack

| Layer | Technologies | Purpose |
|---|---|---|
| Orchestration | LangGraph, LangChain | Stateful agent workflows, routing, tool calls |
| LLM providers | Groq, Google Gemini | Routing, SQL generation, ETL planning |
| Backend | FastAPI, Uvicorn | HTTP API and agent execution |
| Frontend | Streamlit | Chat UI and file download |
| Database | Neon PostgreSQL | Hosted relational database |
| SQL validation | SQLGlot | Parsing and checking generated SQL |
| Data processing | Pandas | JSON normalisation and transformations |
| Config | python-dotenv | Local environment variables |
| Hosting | Render, Streamlit Community Cloud, Neon | Backend, frontend, database |

---

## 7. Project structure

```text
DataSage/
├── Agents/
│   ├── data_agent.py        # Main LangGraph router
│   ├── sql_analyst.py       # SQL analytics agent
│   └── etl_analyst.py       # ETL agent and tool selection
├── Models/
│   └── schema.py            # Shared agent state schemas
├── Guardrails/
│   ├── sql_guard.py         # SQL validation
│   └── etl_guard.py         # ETL plan and path validation
├── utils/
│   ├── database.py          # PostgreSQL connection and schema utilities
│   └── etl_tools.py         # Extraction and transformation tools
├── api/
│   └── main.py              # FastAPI application
├── frontend/
│   └── app.py               # Streamlit frontend
├── data/
│   ├── extract/             # Runtime extraction output
│   └── transform/           # Runtime transformation output
├── data_agent_graph.png
├── sql_agent_graph.png
├── etl_analyst_graph.png
├── feed_db.py               # Load sample CSV data into PostgreSQL
├── pyproject.toml           # Project metadata and dependencies
├── uv.lock                  # Locked dependency versions
├── .env                     # Local secrets (not committed)
└── README.md
```

> `data/extract` and `data/transform` are runtime output folders and may not exist in a fresh clone.

---

## 8. Database and sample data

The SQL workflow runs on PostgreSQL, migrated to **Neon** for the deployed app. `feed_db.py` loads the sample CSVs.

| Table | Records |
|---|---:|
| `users` | 10,000 |
| `vehicles` | 3,000 |
| `rides` | 20,000 |
| `payments` | 16,073 |
| `ratings` | 12,000 |
| **Total** | **61,073** |

---

## 9. Run locally

**Prerequisites:** Python 3.12+, Git, [`uv`](https://docs.astral.sh/uv/), a PostgreSQL database (local or hosted), and API keys for the LLM providers.

**1. Clone and install**

```bash
git clone https://github.com/singhmishal2004-netizen/DATASAGE-Multi-Agent-Orchestration-for-SQL-Analytics-and-ETL-Automation.git
cd DATASAGE-Multi-Agent-Orchestration-for-SQL-Analytics-and-ETL-Automation
uv sync
```

**2. Configure environment** (create `.env` in the project root)

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_groq_model

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model

DATABASE_URL=postgresql://username:password@host:5432/database?sslmode=require
```

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` / `GROQ_MODEL` | Groq key and model identifier |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Gemini key and model identifier |
| `DATABASE_URL` | PostgreSQL connection URL |

Use model identifiers supported by each provider. Never commit `.env` or paste live credentials into code, README files, screenshots or issues. In deployment, set these in the host's secrets settings.

**3. Initialise the database**

```bash
uv run python feed_db.py
```

Check the script's behaviour and back up first if the target database holds important data.

**4. Start the backend**

```bash
uv run uvicorn api.main:app --reload --port 8000
```

API: `http://127.0.0.1:8000` · Docs: `http://127.0.0.1:8000/docs`

**5. Start the frontend** (second terminal)

```bash
uv run streamlit run frontend/app.py
```

UI: usually `http://localhost:8501`

---

## 10. API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Send a natural-language request |
| `GET` | `/download` | Download a generated CSV file |

**Health check**

```bash
curl https://datasage-multi-agent-orchestration-for.onrender.com/health
# {"status": "healthy"}
```

**Chat**

```bash
curl -X POST https://datasage-multi-agent-orchestration-for.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many vehicles are in the database?"}'
```

The response contains the assistant's answer and routing information, as defined by the API response schema.

**Download**

```text
GET /download?file_path=data/transform/transformed_data.csv
```

Only CSV is supported. The backend validates the requested path before returning the file.

---

## 11. Example requests

**SQL analytics**

- How many vehicles are present in the database?
- Show the average rating for each vehicle type.
- Which users have the highest number of rides?
- What is the total payment amount by payment method?

**ETL extraction**

```text
Extract data from https://jsonplaceholder.typicode.com/posts
and save it in data/extract in CSV format.
```

**ETL transformation**

```text
Transform data/extract/extracted_data.csv.
Remove duplicate rows, select the id and title columns,
sort by id in ascending order, and save the output
in data/transform in CSV format.
```

Fields and operations must exist in the input dataset and be supported by the ETL plan validator.

---

## 12. Deployment

```mermaid
flowchart LR
    B[Browser] --> S[Streamlit Community Cloud]
    S -->|HTTPS| R[Render - FastAPI]
    R --> N[(Neon PostgreSQL)]
    R --> X[External APIs]
    R --> F[Generated ETL files]
```

| Component | Platform | Responsibility |
|---|---|---|
| Frontend | Streamlit Community Cloud | UI and chat |
| Backend | Render | FastAPI, agent execution, file responses |
| Database | Neon | Managed PostgreSQL |

**Steps**

1. Push changes to GitHub.
2. Render builds and starts the FastAPI service.
3. Streamlit Community Cloud deploys the frontend from the repository.
4. Set the backend URL in the frontend.
5. Add API keys and the Neon `DATABASE_URL` in each host's secrets settings.
6. Verify `/health`, `/docs`, one SQL request and one ETL extraction/transformation.

**Render settings**

| Setting | Value |
|---|---|
| Build command | `uv sync --frozen` |
| Start command | `uv run uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Backend URL | `https://datasage-multi-agent-orchestration-for.onrender.com` |

**Things to know**

- A free Render service sleeps when idle, so the first request afterwards is slower.
- Its local disk is ephemeral; ETL files can disappear on restart or redeploy. Use object storage for persistence.
- Keep the frontend's backend URL in sync with the Render URL.
- Keep all secrets in host environment settings, never in Git.

---

## 13. Engineering decisions

1. **Routing separated from specialist work.** The Data Agent only identifies intent and delegates, keeping responsibilities clear and the system easy to extend.
2. **Schema context for SQL.** Models guess badly without real table and column names; fetching the schema first avoids many errors.
3. **Generated SQL is untrusted.** A valid query can still be unsafe, so the SQL guard checks it before execution.
4. **ETL behind explicit tools.** User requests become structured plans applied through a fixed set of Pandas operations, never arbitrary generated Python.
5. **UI, API and database kept separate.** Each boundary must be configured correctly: the right backend URL and the right connection string.
6. **Test the deployed workflow.** Check API health, database connectivity, routing, ETL output creation and file downloads, not only local code.

---

## 14. Limitations and roadmap

DataSage is an evolving project. These are next steps, not current features.

- **Auth and authorisation:** protect chat and download endpoints; separate users' data.
- **Durable storage:** move ETL output to object storage.
- **SSRF protection:** restrict extraction URLs, validate resolved IPs, block internal networks.
- **ETL observability:** log metadata, plans, row counts, errors and durations.
- **Automated tests:** SQL validation, ETL plan validation, path containment, API endpoints.
- **Large datasets:** streaming, pagination, chunked processing, resource limits.
- **Conversation persistence:** durable checkpoints for multi-session continuity.
- **Deployment hardening:** rate limiting, structured logs, monitoring, managed secrets.

---

## 15. Author

**Mishal Singh**
Indian Institute of Information Technology Vadodara
GitHub: [singhmishal2004-netizen](https://github.com/singhmishal2004-netizen)

Built as a hands-on exploration of agentic AI, LangGraph orchestration, SQL analytics, ETL automation and full-stack deployment, through an iterative process of building components, connecting them, testing real workflows and fixing integration issues.

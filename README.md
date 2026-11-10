DataSage — Multi-Agent Orchestration for SQL Analytics & ETL Automation
<p align="center">
  <strong>Ask questions about your data. Run guarded SQL analytics. Extract and transform API data — through one conversational interface.</strong>
</p>
<p align="center">
  <img src="data_agent_graph.png" alt="DataSage main Data Agent LangGraph" width="760">
</p>
DataSage is an agentic data assistant built with LangGraph, LangChain, FastAPI, Streamlit, and PostgreSQL. It accepts natural-language requests and routes each task to a specialist: a SQL Analyst for read-only database analytics, or an ETL Analyst for API extraction and controlled data transformations.
The goal was not simply to connect an LLM to a database. The project brings together agent orchestration, tool execution, validation, database context, a usable interface, and a cloud deployment in one end-to-end application.
---
Contents
What DataSage does
Live application
Architecture
Agent workflows
Safety and validation
Technology stack
Project structure
Database and sample data
Run locally
Environment configuration
API reference
Example requests
Deployment architecture
Engineering decisions and lessons
Current limitations and future improvements
Author
---
What DataSage does
DataSage supports two main categories of work.
Capability	What you can ask it to do	What happens
SQL analytics	Ask questions about users, rides, vehicles, payments, and ratings	The SQL Analyst gathers schema context, generates a query, validates it, executes it, and explains the result
API extraction	Extract data from a public JSON API	The ETL Analyst calls the extraction tool and saves the returned records in a supported file format
Data transformation	Clean, select, rename, sort, or reshape an existing dataset	The ETL Analyst creates a structured transformation plan and the ETL utility applies supported Pandas operations
File download	Retrieve generated CSV output from the deployed application	The frontend requests the file from the backend download endpoint
Design principles
Specialized agents instead of one overloaded prompt: routing, SQL analysis, and ETL work have separate responsibilities.
Schema-aware SQL generation: the SQL agent obtains database structure before composing a query.
Validation before execution: generated SQL and ETL plans pass through application-level checks.
Tools perform the work: agents select tools; Python utilities and the database carry out the operations.
Separate frontend and backend: Streamlit handles the user experience while FastAPI exposes the application API.
---
Live application
The deployed architecture uses:
Frontend: Streamlit Community Cloud
Backend: Render Web Service
Database: Neon PostgreSQL
The backend's health endpoint can be checked here:
API health: https://datasage-multi-agent-orchestration-for.onrender.com/health
Interactive API documentation: https://datasage-multi-agent-orchestration-for.onrender.com/docs
> Add your Streamlit Community Cloud app URL here once you want it displayed publicly.
---
Architecture
High-level system architecture
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
Deployment request flow
```mermaid
flowchart LR
    B[Browser] --> S[Streamlit Community Cloud]
    S -->|HTTPS requests| R[Render - FastAPI]
    R --> N[(Neon PostgreSQL)]
    R --> X[External APIs]
    R --> F[Generated ETL files]
```
Agent graph visualizations
The following images are stored in the repository root. GitHub renders them directly in this README.
Main Data Agent graph
![Data Agent graph](data_agent_graph.png)
SQL Analyst graph
![SQL Analyst graph](sql_agent_graph.png)
ETL Analyst graph
![ETL Analyst graph](etl_analyst_graph.png)
---
Agent workflows
1. Data Agent — routing
File: `Agents/data_agent.py`
The Data Agent is the entry point to the agentic workflow. It receives the user's natural-language message and determines which specialist should handle it.
SQL-oriented requests are routed to the SQL Analyst.
Extraction or transformation requests are routed to the ETL Analyst.
The selected agent processes the task and returns its result through the graph.
This separation keeps the top-level agent focused on intent routing and orchestration, rather than mixing database and ETL implementation details into one agent.
2. SQL Analyst — database analytics
File: `Agents/sql_analyst.py`
The SQL Analyst translates a question into a database operation. Its workflow is designed around database context and query validation.
Understand and refine the user's question.
Retrieve relevant schema information from PostgreSQL.
Construct a prompt containing the question and database context.
Generate the SQL query.
Validate the generated query using the SQL guard.
Execute an accepted query against PostgreSQL.
Return a human-readable answer.
Example questions
How many vehicles are present in the database?
Show the average rating for each vehicle type.
Which users have the highest number of rides?
What is the total payment amount by payment method?
SQL Analyst graph
![SQL Analyst workflow](sql_agent_graph.png)
3. ETL Analyst — extraction and transformation
File: `Agents/etl_analyst.py`
The ETL Analyst handles data that comes from external APIs or existing files. It uses dedicated tools from `utils/etl_tools.py`.
Extraction workflow
The user supplies an API URL, output folder, and output format.
The ETL agent selects `extract_load_tool`.
The extraction utility makes the HTTP request and reads the JSON response.
Pandas normalizes the returned records into a tabular structure.
The dataset is saved under the requested data directory.
The extraction utility supports CSV, JSON, and Parquet output formats.
Transformation workflow
The user identifies an input file and describes the desired changes.
The agent reads a small preview of the input dataset for context.
The LLM produces a structured transformation plan.
The plan is validated before it is applied.
The ETL utility executes the supported Pandas operations.
The transformed dataset is saved in the requested format.
Supported operations in the current ETL utility include:
Remove duplicate rows
Remove rows containing null values in selected columns
Fill null values in a selected column
Rename columns
Select columns
Sort values
Typical output locations:
```text
data/
├── extract/
│   └── extracted_data.csv
└── transform/
    └── transformed_data.csv
```
ETL Analyst graph
![ETL Analyst workflow](etl_analyst_graph.png)
---
Safety and validation
LLM-generated instructions should not be treated as trusted code. DataSage therefore places validation between model output and execution.
SQL guard
File: `Guardrails/sql_guard.py`
The SQL guard uses SQLGlot to inspect generated SQL before it reaches the database. The application is intended for read-only analytics and blocks destructive or modifying statements such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, and `ALTER`.
The purpose is to reduce the risk of an incorrect or maliciously influenced model response changing the database.
ETL guard
File: `Guardrails/etl_guard.py`
The ETL guard validates transformation plans and restricts file operations to the project's data directory. It also validates supported output formats.
The transformation workflow uses an allowlisted set of operations rather than executing arbitrary Python code produced by an LLM.
Important security note
These controls are application-level safeguards, not a guarantee of complete security. Before exposing the service to untrusted users or production workloads, add authentication and authorization, rate limiting, stricter API destination validation/SSRF protection, resource limits, and appropriate database permissions. The download endpoint should also be protected if files are private.
---
Technology stack
Layer	Technologies	Purpose
Agent orchestration	LangGraph, LangChain	State-driven agent workflows, routing, and tool calls
LLM providers	Groq, Google Gemini	Natural-language understanding, routing, SQL generation, and ETL planning
Backend	FastAPI, Uvicorn	HTTP API and application execution
Frontend	Streamlit	Chat interface and ETL file download experience
Database	Neon PostgreSQL	Hosted relational database
SQL validation	SQLGlot	Parsing and checking generated SQL
Data processing	Pandas	JSON normalization and dataset transformations
Configuration	python-dotenv	Local environment-variable loading
Deployment	Render, Streamlit Community Cloud, Neon	Backend, frontend, and database hosting
---
Project structure
```text
DataSage/
│
├── Agents/
│   ├── data_agent.py          # Main LangGraph router
│   ├── sql_analyst.py          # SQL analytics agent
│   └── etl_analyst.py          # ETL agent and tool selection
│
├── Models/
│   └── schema.py              # Shared agent state schemas
│
├── Guardrails/
│   ├── sql_guard.py           # SQL validation
│   └── etl_guard.py           # ETL plan and path validation
│
├── utils/
│   ├── database.py            # PostgreSQL connection and schema utilities
│   └── etl_tools.py           # Extraction and transformation tools
│
├── api/
│   └── main.py                # FastAPI application
│
├── frontend/
│   └── app.py                 # Streamlit frontend
│
├── data/
│   ├── extract/               # Runtime extraction output
│   └── transform/             # Runtime transformation output
│
├── data_agent_graph.png       # Main agent graph
├── sql_agent_graph.png        # SQL agent graph
├── etl_analyst_graph.png      # ETL agent graph
│
├── feed_db.py                 # Load sample CSV data into PostgreSQL
├── pyproject.toml             # Project metadata and dependencies
├── uv.lock                    # Locked dependency versions
├── .env                       # Local secrets (not committed)
└── README.md
```
> The `data/extract` and `data/transform` folders are runtime output locations. Generated files should not be assumed to exist in a fresh clone.
---
Database and sample data
DataSage uses PostgreSQL for its SQL analytics workflow. The project database was migrated to Neon PostgreSQL for the deployed application.
The sample relational dataset contains the following tables:
Table	Records loaded
`users`	10,000
`vehicles`	3,000
`rides`	20,000
`payments`	16,073
`ratings`	12,000
Total	61,073
The `feed_db.py` script loads the CSV datasets into PostgreSQL. The SQL Analyst can then use the database schema as context when answering natural-language questions.
---
Run locally
Prerequisites
Python 3.12 or later
Git
`uv` package manager
PostgreSQL database (local or hosted)
API keys for the configured LLM providers
1. Clone the repository
```bash
git clone https://github.com/singhmishal2004-netizen/DATASAGE-Multi-Agent-Orchestration-for-SQL-Analytics-and-ETL-Automation.git
cd DATASAGE-Multi-Agent-Orchestration-for-SQL-Analytics-and-ETL-Automation
```
2. Install dependencies
If `uv` is not installed, install it using the official instructions at https://docs.astral.sh/uv/.
Then run:
```bash
uv sync
```
3. Configure environment variables
Create a `.env` file in the project root. Use the variable names expected by your current application configuration.
```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_groq_model

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model

DATABASE_URL=postgresql://username:password@host:5432/database?sslmode=require
```
Never commit `.env` or paste live credentials into source code, README files, screenshots, or issue reports. For deployment, configure the same values in the hosting provider's environment/secrets settings.
4. Initialize the database
Make sure `DATABASE_URL` points to the database you intend to use. Then run:
```bash
uv run python feed_db.py
```
The script loads the project's sample CSV data into PostgreSQL. Avoid running an initialization script against a database containing important data unless you have checked its behavior and backed up the database.
5. Start the FastAPI backend
From the project root:
```bash
uv run uvicorn api.main:app --reload --port 8000
```
The API will be available at:
```text
http://127.0.0.1:8000
```
Interactive API documentation:
```text
http://127.0.0.1:8000/docs
```
6. Start the Streamlit frontend
Open a second terminal in the project root:
```bash
uv run streamlit run frontend/app.py
```
The Streamlit application will print its local URL, usually:
```text
http://localhost:8501
```
---
Environment configuration
Variable	Purpose
`GROQ_API_KEY`	API key for Groq
`GROQ_MODEL`	Groq model identifier used by the application
`GEMINI_API_KEY`	API key for Google Gemini
`GEMINI_MODEL`	Gemini model identifier used by the application
`DATABASE_URL`	PostgreSQL connection URL
Use the exact model identifiers supported by the provider and configured in your code. Do not copy example credentials into a real environment.
---
API reference
The FastAPI backend exposes the following application endpoints:
Method	Endpoint	Purpose
`GET`	`/health`	Health check
`POST`	`/chat`	Send a natural-language request to DataSage
`GET`	`/download`	Download a generated CSV file
Health check
```bash
curl https://datasage-multi-agent-orchestration-for.onrender.com/health
```
Expected response:
```json
{
  "status": "healthy"
}
```
Chat request
```bash
curl -X POST \
  https://datasage-multi-agent-orchestration-for.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many vehicles are in the database?"}'
```
The response includes the assistant's answer and routing information as defined by the API response schema.
Download an ETL output
The download endpoint accepts a `file_path` query parameter. For example:
```text
GET /download?file_path=data/transform/transformed_data.csv
```
Only CSV downloads are supported by the current download endpoint. The backend validates the requested path before returning a file.
---
Example requests
These are examples of natural-language requests you can enter in the DataSage chat interface.
SQL analytics
```text
How many vehicles are present in the database?
```
```text
Show the average rating for each vehicle type.
```
```text
Find the total number of rides for each user.
```
```text
Show the payment distribution by payment method.
```
ETL extraction
```text
Extract data from https://jsonplaceholder.typicode.com/posts
and save it in data/extract in CSV format.
```
```text
Extract data from https://pokeapi.co/api/v2/pokemon
and save it in data/extract in CSV format.
```
ETL transformation
```text
Transform data/extract/extracted_data.csv.
Remove duplicate rows, select the id and title columns,
sort by id in ascending order, and save the output
in data/transform in CSV format.
```
The exact fields and transformation operations must exist in the input dataset and be supported by the current ETL plan validator.
---
Deployment architecture
DataSage is split into three independently hosted components.
Component	Hosting platform	Responsibility
Frontend	Streamlit Community Cloud	User interface and chat interaction
Backend	Render	FastAPI endpoints, agent execution, and file responses
Database	Neon	Managed PostgreSQL database
Deployment flow
Push application changes to the GitHub repository.
Render builds and starts the FastAPI service.
Streamlit Community Cloud deploys the frontend from the repository.
Configure the backend URL in the frontend.
Add API keys and the Neon `DATABASE_URL` through the hosting providers' secrets/environment settings.
Verify `/health`, `/docs`, a SQL request, and an ETL extraction/transformation request.
Render configuration
Build command
```bash
uv sync --frozen
```
Start command
```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
The deployed backend URL:
```text
https://datasage-multi-agent-orchestration-for.onrender.com
```
Deployment considerations
A free Render web service may sleep when idle, so its first request after inactivity can take longer.
The local filesystem of a free web service is ephemeral. Files written by an ETL run may disappear after a restart or redeployment.
For persistent ETL output, use object storage or another durable file store rather than relying on the service's local disk.
Keep the frontend's backend URL and the Render service URL in sync.
Store all secrets in hosting environment settings, never in Git.
---
Engineering decisions and lessons
This project involved more than implementing individual agents. A major part of the work was making the pieces operate together reliably.
1. Separating routing from specialist work
The Data Agent does not need to know how to perform every SQL or ETL operation. It identifies the task and delegates it. This keeps agent responsibilities clearer and makes the system easier to extend.
2. Supplying database schema context
Natural-language-to-SQL generation is unreliable when the model does not know the actual table and column names. Fetching schema information before query generation gives the SQL Analyst relevant database context and reduces avoidable schema errors.
3. Treating generated SQL as untrusted
A model can produce a syntactically valid query that is still unsafe. The SQL guard therefore checks the generated statement before execution. The application is designed for read-only analytics rather than general database administration.
4. Moving ETL execution behind explicit tools
Instead of allowing an LLM to execute arbitrary generated Python, the ETL workflow converts the user's request into a structured plan and applies a defined set of Pandas operations. This makes the execution path easier to validate and reason about.
5. Separating the UI, API, and database
Deploying Streamlit, FastAPI, and PostgreSQL as separate services makes their responsibilities explicit. It also means each boundary must be configured correctly: the frontend must call the right backend URL, and the backend must use the correct database connection string.
6. Testing the deployed workflow, not only the local code
A feature is not complete just because it works locally. The deployed application also needs checks for API health, database connectivity, agent routing, ETL output creation, and file downloads.
---
Current limitations and future improvements
DataSage is an evolving project. The following are useful next steps rather than claims that the current version already implements them.
Authentication and authorization: protect chat and download endpoints and separate users' data.
Persistent artifact storage: move ETL output from ephemeral service storage to durable object storage.
SSRF protection: restrict extraction URLs, validate resolved IP addresses, and block private or internal network destinations.
ETL observability: record extraction metadata, transformation plans, row counts, errors, and execution duration.
Automated tests: add unit tests for SQL validation, ETL plan validation, path containment, and API endpoints.
Large dataset handling: add streaming, pagination, chunked processing, and resource limits where appropriate.
Conversation persistence: add durable conversation/checkpoint storage if multi-session continuity is required.
Deployment hardening: add rate limiting, structured logs, monitoring, and production-grade secret management.
---
Author
Mishal Singh  
Indian Institute of Information Technology Vadodara  
GitHub: singhmishal2004-netizen
---
Acknowledgements
Built as a hands-on exploration of agentic AI, LangGraph orchestration, SQL analytics, ETL automation, and full-stack deployment. The project reflects an iterative engineering process: building individual components, connecting them, testing real workflows, diagnosing integration issues, and improving the system based on those results.

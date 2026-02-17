# Clinical Document Indexing Sandbox

This repository is a sandbox for clinical document indexing, query, and retrieval experiments.

## Objective
Build and evaluate a lightweight retrieval system over clinical-style documents (currently synthetic IPS-style patient summaries), with an interactive agent interface for question answering.

## Architecture Framework Alignment
This README follows your preferred architecture framing (coverage + process + representation), inspired by C4, TOGAF ADM, and Zachman.
Reference framework: https://github.com/aaronaston/architecture/blob/main/docs/architecture-framework.md

### Coverage (What / How / Where / Who / When / Why)
- What: Synthetic patient markdown documents and reference clinical forms.
- How: Python CLI app using LlamaIndex + OpenAI, with in-memory indexing and tool-based agent retrieval.
- Where: Local workstation, local filesystem, OpenAI API.
- Who: Developer/operator running scripts and querying the agent.
- When: Reindex on every startup; no persistence across restarts.
- Why: Fast iteration for extraction/indexing/retrieval experiments without data lifecycle complexity.

### Process (ADM-Inspired)
- Phase A (Vision): Validate clinical retrieval patterns quickly.
- Phase B/C (Business + Information Systems): Represent each patient summary as a whole-document retrieval unit.
- Phase D (Technology): Use Python venv + LlamaIndex + OpenAI.
- Phase E/F (Opportunities + Migration): Evolve from in-memory CLI to service/API + persistent index when evaluation stabilizes.
- Phase G/H (Governance + Change): Keep scripts deterministic and test-data-only; restart refreshes state.

### Representation (C4-Oriented)
- System Context:
  - Actor: User in terminal.
  - System: `patient_index_agent.py`.
  - External dependency: OpenAI API (LLM + embeddings).
  - Data source: `test-data/patients/*.md`.
- Container View:
  - One Python process hosting index build, query engine, and agent loop.
- Component View:
  - Index builder: reads markdown, creates one `TextNode` per file.
  - Retrieval tool: semantic search over `VectorStoreIndex`.
  - Agent: `FunctionAgent` with chat context and tool use.
  - CLI shell: readline-backed interactive prompt with message history.

## Current Solution Design

### Data Assets
- `reference/forms`
  - Source clinical forms (for example Ontario lab requisition PDFs)
- `test-data/patients`
  - 30 synthetic IPS-style patient summaries
- `test-data/OntarioLabReq-4422-84-sample-filled.pdf`
  - Generated filled example for parsing/indexing experiments

### Scripts
- `scripts/generate_patients.py`
  - Regenerates synthetic patient summaries in `test-data/patients`
- `scripts/fill_lab_req_sample.py`
  - Fills the Ontario lab requisition sample PDF
- `scripts/patient_index_agent.py`
  - Builds in-memory index and starts interactive retrieval agent
- `scripts/setup_venv.sh`
  - Creates `.venv` and installs dependencies
- `start-agent.sh`
  - Convenience launcher for environment + API key + agent startup

## LlamaIndex Usage Details
The agent implementation in `scripts/patient_index_agent.py` uses:
- `VectorStoreIndex`
  - Built from explicit `TextNode` objects.
  - Node granularity is full file, one node per patient markdown file (no chunk splitting).
- Query engine
  - Created via `index.as_query_engine(similarity_top_k=4)`.
- Agent
  - `FunctionAgent` with tools:
    - `search_patient_documents(query)`
    - `count_patient_documents()`
  - `Context(agent)` is preserved for the process lifetime to maintain chat history.
- Citations
  - Tool output includes source file citations with full absolute paths.
- Persistence model
  - No vector store persistence.
  - Restarting the process rebuilds index from filesystem.

## Runtime Flow
1. Start script loads environment and API key.
2. Agent script reads all patient markdown files.
3. Index is built in memory.
4. User asks questions in terminal.
5. Agent invokes retrieval tool(s), then returns response.
6. Tool output is printed in faded/dim text for visibility.
7. Session history remains in memory only.

## Python Environment
This project uses a local virtual environment at `.venv`.

Create/update environment and install dependencies:

```bash
scripts/setup_venv.sh
```

Dependencies are defined in `requirements.txt` and include:
- LlamaIndex (`llama-index`, `llama-index-llms-openai`, `llama-index-embeddings-openai`)
- OpenAI SDK (`openai`)
- Existing PDF/form utilities (`pypdf`, `cryptography`, `pymupdf`)

## Start the Agent
From repo root:

```bash
chmod u+x start-agent.sh
./start-agent.sh
```

Notes:
- `chmod u+x start-agent.sh` is only needed if executable permission is missing.
- `start-agent.sh` will create `.venv` automatically if it does not exist.
- Put your key in `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

## Working with Test Data
Regenerate synthetic patients:

```bash
source .venv/bin/activate
python3 scripts/generate_patients.py
```

Generate filled Ontario requisition sample:

```bash
source .venv/bin/activate
python3 scripts/fill_lab_req_sample.py
```

Input/output for form fill:
- Input: `reference/forms/OntarioLabReq-4422-84.pdf`
- Output: `test-data/OntarioLabReq-4422-84-sample-filled.pdf`

## Non-Goals (Current Stage)
- No production security hardening.
- No persistent vector database.
- No multi-user session management.
- No formal PHI pipeline.

## Data Safety
- Treat repository content as test/synthetic unless explicitly marked otherwise.
- Do not add real PHI/PII without governance, controls, and legal approval.

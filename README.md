# Clinical Document Indexing Sandbox

This repository is a sandbox for clinical document indexing, query, and retrieval experiments.

## Objective
Build and evaluate a lightweight retrieval system over clinical-style documents (currently synthetic IPS-style patient summaries), with an interactive agent interface for question answering.

## Architecture Framework Alignment
This README follows your preferred architecture framing (coverage + process + representation), inspired by C4, TOGAF ADM, and Zachman.
Reference framework: https://github.com/aaronaston/architecture/blob/main/docs/architecture-framework.md

### Coverage (What / How / Where / Who / When / Why)
- What: Synthetic patient markdown documents, encounter histories with SOAP notes, practitioner/organization rosters, and reference clinical forms.
- How: Python CLI app using LlamaIndex + OpenAI + HuggingFace MedEmbed, with hybrid BM25+vector retrieval, LLM reranking, and section-aware chunking.
- Where: Local workstation, local filesystem, OpenAI API, HuggingFace model hub (model cached locally after first download).
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
  - Data source: `test-data/patients/*.md`, `test-data/encounters/*.md`, `test-data/practitioners/`, `test-data/organizations/`.
- Container View:
  - One Python process hosting index build, hybrid query engine, and agent loop.
- Component View:
  - **Chunker**: reads each patient file, splits into one `TextNode` per `##` section with enriched metadata (patient name, ID, section type).
  - **Embedder**: `HuggingFaceEmbedding` using `abhinand/MedEmbed-small-v0.1` for clinical-domain synonym awareness.
  - **Hybrid Retriever**: `VectorIndexRetriever` + `BM25Retriever` fused via `QueryFusionRetriever` (Reciprocal Rank Fusion).
  - **Reranker**: `LLMRerank` reduces top-20 fused candidates to top-4 before LLM synthesis.
  - **Agent**: `FunctionAgent` with `search_patient_documents` / `count_patient_documents` tools and persistent chat context.
  - CLI shell: readline-backed interactive prompt with message history.

## Current Solution Design

### Data Assets
- `reference/forms`
  - Source clinical forms (for example Ontario lab requisition PDFs)
- `test-data/patients` — 30 synthetic IPS-style patient summaries
- `test-data/practitioners/practitioners.md` — Roster of ~25 practitioners (family physicians, walk-in clinic physicians, emergency physicians, specialists, nurse practitioners) with practitioner numbers, CPSO registrations, and organization affiliations
- `test-data/organizations/organizations.md` — Roster of ~19 organizations (family health teams, walk-in clinics, hospitals, specialist clinics) across Ontario with addresses, hours, and services
- `test-data/encounters/` — 30 encounter history files (one per patient), covering Feb 2024 – Feb 2026 with full SOAP notes. ~197 encounters total across three complexity tiers:
  - **High** (10 patients, ~10 encounters each): complex chronic disease, multi-specialist, emergency visits
  - **Moderate** (13 patients, ~5-6 encounters each): stable chronic conditions, periodic follow-ups
  - **Low** (7 patients, ~3-4 encounters each): healthy / single mild condition, annual visits
- `test-data/OntarioLabReq-4422-84-sample-filled.pdf`
  - Generated filled example for parsing/indexing experiments (corresponds to encounter 4 in `21-AaronAston.md`)

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
- **Chunking** (`build_nodes`)
  - Splits each IPS patient markdown on `##` section headings.
  - Each `TextNode` carries metadata: `patient_id`, `patient_name`, `section`, `file_name`.
- **Embeddings** (`HuggingFaceEmbedding`)
  - Model: `abhinand/MedEmbed-small-v0.1` — fine-tuned on clinical data.
  - Cached locally to `~/.cache/huggingface` after first download.
  - Set globally via `Settings.embed_model` so the index and query share the same model.
- **Hybrid Retrieval** (`build_query_engine`)
  - `VectorIndexRetriever` — dense semantic similarity search (top 20).
  - `BM25Retriever` — sparse BM25 keyword search (top 20).
  - `QueryFusionRetriever` with `mode="reciprocal_rerank"` — merges both ranked lists.
- **Reranking**
  - `LLMRerank(top_n=4)` — scores each `(query, chunk)` pair and keeps the 4 most relevant.
- **Agent**
  - `FunctionAgent` with tools:
    - `search_patient_documents(query)` — runs full hybrid pipeline.
    - `count_patient_documents()` — returns number of indexed files.
  - `Context(agent)` is preserved for the process lifetime to maintain chat history.
- **Citations**
  - Tool output includes `file_name`, `section`, and `patient_name` per source chunk.
- **Persistence model**
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
- No persistent vector database (Qdrant/Milvus would be the next step).
- No multi-user session management.
- No formal PHI pipeline.
- No Cohere/external reranker API (LLMRerank used instead to avoid extra keys).

## Data Safety
- Treat repository content as test/synthetic unless explicitly marked otherwise.
- Do not add real PHI/PII without governance, controls, and legal approval.

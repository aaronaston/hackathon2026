# Project Context: Patient Intelligence Explorer (EMR AI Assistant)

## Project Overview
This project is an EMR (Electronic Medical Record) explorer application enhanced with a clinical AI assistant built using `llama-index`. The goal is to allow clinicians to query patient summaries (IPS) and historical encounter notes (SOAP format) using natural language, and generate clinical metric charts on the fly.

## Architecture
*   **Backend**: Python 3 standard library `http.server`.
    *   `scripts/patient_index_agent.py`: Contains the core AI pipeline. Uses `FunctionAgent` with `gpt-5.1` (or `gpt-4o`), `HuggingFaceEmbedding` (`abhinand/MedEmbed-small-v0.1`), BM25 Retriever, and `LLMRerank`.
    *   `scripts/patient_web_app.py`: The web server. Hosts the static frontend and serves `/api/` endpoints.
*   **Frontend**: Vanilla HTML / CSS / JS located in the `web/` directory (`index.html`, `styles.css`, `app.js`).
*   **Data**: Markdown files in `test-data/patients` and `test-data/encounters`.

## Recent Accomplishments
1.  **Hybrid Search Implementation**: Upgraded the `search_patient_documents` tool to use a `QueryFusionRetriever` combining Semantic Vector Search and BM25, followed by `LLMRerank` (top N=4 results).
2.  **Encounter Indexing**: Added a `chunk_encounter_file` parser. The global index now contains ~300 patient chunks and ~1,188 encounter SOAP chunks.
3.  **On-the-Fly Charting**: Implemented an `extract_and_chart` tool for the agent. It retrieves encounter chunks containing a metric, uses GPT to extract `{date, value, unit}`, renders a `matplotlib` chart, saves a PNG to the `charts/` directory, and auto-opens it on macOS.
4.  **Backend Chat API**: We just added a `/api/chat` Server-Sent Events (SSE) endpoint to `scripts/patient_web_app.py`. This endpoint initializes the `patient_index_agent` pipeline in a background thread and streams text updates and base64-encoded charts back to the client.

## Current State & Next Steps
We are currently in the middle of building a **floating chat widget overlay** for the frontend EMR web app.

**What's Done**:
*   The backend `/api/chat` SSE endpoint is implemented in `patient_web_app.py`. It successfully streams `status`, `tool_call`, `chart` (base64 image), `reply`, and `error` events.

**What Needs to be Done Next**:
1.  **Frontend HTML/CSS**: Add the floating chat widget UI (a toggle button and a chat panel) to `web/index.html` and `web/styles.css`. It needs to look modern and integrate smoothly.
2.  **Frontend JS Integration**: Update `web/app.js` to handle opening/closing the chat widget, accepting user input, connecting to the `/api/chat` SSE endpoint, and rendering the streamed text and base64 chart images into the chat UI.

#!/usr/bin/env python3
"""
Patient document agent — upgraded hybrid search pipeline.

Pipeline:
  1. Section-aware chunking   – one TextNode per IPS section (not per file)
  2. Medical embeddings       – abhinand/MedEmbed-small-v0.1 (clinical synonyms)
  3. Hybrid retrieval         – BM25 + vector fusion via Reciprocal Rank Fusion
  4. Reranking                – LLMRerank to surface the 4 most relevant chunks
  5. Agent                    – FunctionAgent with chat history preserved
"""

import asyncio
import json
import re
import os
import tempfile
from datetime import datetime
from pathlib import Path
import readline

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe inside async event loop
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import TextNode
from llama_index.core.workflow import Context
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.retrievers.bm25 import BM25Retriever

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR  = PROJECT_ROOT / "test-data" / "patients"
ENCOUNTER_DIR = PROJECT_ROOT / "test-data" / "encounters"

# ----- Models ---------------------------------------------------------------
LLM_MODEL = "gpt-5.1"
EMBED_MODEL_ID = "abhinand/MedEmbed-small-v0.1"

# ----- Retrieval config -----------------------------------------------------
# Hybrid retriever fetches more candidates so reranker has room to work
HYBRID_TOP_K = 20   # candidates returned by each retriever before fusion
RERANK_TOP_N = 4    # final chunks sent to the LLM after reranking


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_faded(text: str) -> None:
    """Print tool/debug output in dim gray."""
    print(f"\033[90m{text}\033[0m", flush=True)


def print_header(text: str) -> None:
    """Print a highlighted startup banner line."""
    print(f"\033[1;36m{text}\033[0m", flush=True)


# ---------------------------------------------------------------------------
# Phase 1 – Section-aware chunking
# ---------------------------------------------------------------------------

def _parse_patient_header(text: str) -> dict:
    """Extract patient name and a numeric patient ID from the ## Patient block."""
    meta = {}
    m = re.search(r"- Name:\s*(.+)", text)
    if m:
        meta["patient_name"] = m.group(1).strip()
    return meta


def chunk_patient_file(path: Path) -> list[TextNode]:
    """
    Split one IPS patient markdown file into one TextNode per ## section.

    Key design decisions to avoid false positives:
    - The TEXT stored for embedding is: "Patient: {name} | Section: {section}\\n{content_body}"
      NOT the raw markdown with heading. This means the word "Allergies" in the heading
      does NOT inflate similarity scores for 'No known allergies' chunks.
    - `has_finding` metadata = True only if content is a positive clinical finding
      (i.e. not "No known X" or "None").
    - Both the section name and the original full text are in metadata for display/BM25.
    """
    text = path.read_text(encoding="utf-8")
    patient_id = path.stem.split("-")[0]
    shared_meta = {"patient_id": patient_id, "file_name": path.name}
    shared_meta.update(_parse_patient_header(text))
    patient_name = shared_meta.get("patient_name", "Unknown")

    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    nodes = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        heading_match = re.match(r"^## (.+)", part)
        if heading_match:
            section = heading_match.group(1).strip()
            section = re.sub(r"\s*\(.*?\)", "", section).strip()
            # Content is everything after the heading line
            body_lines = part.split("\n")[1:]
            content_body = "\n".join(body_lines).strip()
        else:
            section = "Header"
            content_body = part

        # Detect negative findings ("No known X", "None", "Not applicable")
        content_lower = content_body.lower()
        is_negative = any(
            phrase in content_lower
            for phrase in ["no known", "none.", "none\n", "not applicable", "no recent abnormal", "no current"]
        )
        has_finding = not is_negative and bool(content_body.strip())

        # Embed richly-contextualised text WITHOUT the heading keyword.
        # This prevents heading words like "Allergies" from inflating scores
        # for chunks whose content is "No known drug allergies."
        embed_text = f"Patient: {patient_name} | Section: {section}\n{content_body}"

        # For the Patient section, enrich embed text with resolved country/province name
        # so queries like "patients in Canada" or "patients in Ontario" resolve correctly.
        # Patient files only store province codes (e.g. "ON") — the word "Canada" never appears.
        _CA_PROVINCES = {
            "ON": "Ontario", "BC": "British Columbia", "AB": "Alberta",
            "QC": "Quebec", "MB": "Manitoba", "SK": "Saskatchewan",
            "NS": "Nova Scotia", "NB": "New Brunswick", "NL": "Newfoundland",
            "PE": "Prince Edward Island", "YT": "Yukon", "NT": "Northwest Territories",
            "NU": "Nunavut",
        }
        if section == "Patient":
            for code, province_name in _CA_PROVINCES.items():
                if f", {code} " in content_body or f", {code}\n" in content_body:
                    embed_text += f"\nCountry: Canada | Province: {province_name}"
                    break

        node_meta = {
            **shared_meta,
            "section": section,
            "has_finding": has_finding,
            "content_preview": content_body[:120],
        }
        nodes.append(TextNode(text=embed_text, metadata=node_meta))

    return nodes



def chunk_encounter_file(path: Path) -> list[TextNode]:
    """
    Split one encounter markdown file into one TextNode per SOAP section.

    Structure of encounter files:
      # Encounters: {Patient Name}
      ## Patient Demographics   <-- skip (already in patient summary)
      ## Encounter N: {date} — {reason}
      ### Subjective / Objective / Assessment / Plan / Disposition

    Each chunk gets metadata:
      document_type  = "encounter"
      encounter_date = "YYYY-MM-DD"
      encounter_reason = brief reason string
      encounter_num  = integer
      soap_section   = "Subjective" | "Objective" | "Assessment" | "Plan" | ...
      patient_name, patient_id, file_name
    """
    text = path.read_text(encoding="utf-8")
    patient_id = path.stem.split("-")[0]

    # Extract patient name from the file title line
    title_match = re.match(r"# Encounters: (.+)", text)
    patient_name = title_match.group(1).strip() if title_match else path.stem

    shared_meta = {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "file_name": path.name,
        "document_type": "encounter",
    }

    nodes = []

    # Split into per-encounter blocks on `## Encounter N:` headings
    encounter_blocks = re.split(r"(?=^## Encounter \d+:)", text, flags=re.MULTILINE)

    for block in encounter_blocks:
        block = block.strip()
        if not block or block.startswith("# ") or block.startswith("## Patient"):
            continue  # skip file title and demographics header

        # Parse encounter header: ## Encounter 2: 2024-11-18 — Croup ...
        enc_header = re.match(r"^## Encounter (\d+): (\d{4}-\d{2}-\d{2}) — (.+)", block)
        if not enc_header:
            continue
        enc_num    = int(enc_header.group(1))
        enc_date   = enc_header.group(2).strip()
        enc_reason = enc_header.group(3).strip()

        enc_meta = {
            **shared_meta,
            "encounter_num": enc_num,
            "encounter_date": enc_date,
            "encounter_reason": enc_reason,
        }

        # Split the encounter block into ### SOAP sub-sections
        soap_blocks = re.split(r"(?=^### )", block, flags=re.MULTILINE)
        for soap_block in soap_blocks:
            soap_block = soap_block.strip()
            if not soap_block:
                continue

            soap_match = re.match(r"^### (.+)", soap_block)
            if soap_match:
                soap_section = soap_match.group(1).strip()
                content_body = "\n".join(soap_block.split("\n")[1:]).strip()
            else:
                # The intro lines of the encounter (date, type, org, practitioner)
                soap_section = "Encounter Header"
                content_body = soap_block

            if not content_body:
                continue

            # Detect negative findings
            content_lower = content_body.lower()
            is_negative = any(
                phrase in content_lower
                for phrase in ["no known", "none.", "none\n", "not applicable",
                               "no recent abnormal", "no current", "no acute"]
            )
            has_finding = not is_negative and bool(content_body.strip())

            # Rich embed text: patient + date + reason + SOAP section + content
            embed_text = (
                f"Patient: {patient_name} | Date: {enc_date} | "
                f"Visit: {enc_reason} | Section: {soap_section}\n"
                f"{content_body}"
            )

            node_meta = {
                **enc_meta,
                "section": soap_section,
                "has_finding": has_finding,
                "content_preview": content_body[:120],
            }
            nodes.append(TextNode(text=embed_text, metadata=node_meta))

    return nodes


def build_nodes() -> list[TextNode]:
    """
    Build all TextNodes from:
    - Patient IPS summaries  (test-data/patients/*.md)   — one node per ## section
    - Encounter SOAP notes   (test-data/encounters/*.md) — one node per ### SOAP section
    """
    all_nodes: list[TextNode] = []

    for path in sorted(PATIENT_DIR.glob("*.md")):
        all_nodes.extend(chunk_patient_file(path))

    if ENCOUNTER_DIR.exists():
        for path in sorted(ENCOUNTER_DIR.glob("*.md")):
            all_nodes.extend(chunk_encounter_file(path))

    if not all_nodes:
        raise RuntimeError(f"No markdown files found in {PATIENT_DIR}")
    return all_nodes


# ---------------------------------------------------------------------------
# Phase 2 – Configure medical embeddings globally
# ---------------------------------------------------------------------------

def configure_settings(llm: OpenAI) -> None:
    """Set the global LlamaIndex Settings so all components share the same models."""
    Settings.llm = llm
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_ID,
        trust_remote_code=True,
    )


# ---------------------------------------------------------------------------
# Phase 3+4 – Build the hybrid retrieval + reranking query engine
# ---------------------------------------------------------------------------

def build_query_engine(nodes: list[TextNode], llm: OpenAI) -> RetrieverQueryEngine:
    """
    Build:
      - VectorIndexRetriever  (dense semantic search via MedEmbed)
      - BM25Retriever         (sparse lexical search — exact keyword match)
      - QueryFusionRetriever  (RRF merger of both)
      - LLMRerank postprocessor
    Return a RetrieverQueryEngine over the fused pipeline.
    """
    # Phase 2: index uses Settings.embed_model (MedEmbed) automatically
    index = VectorStoreIndex(nodes=nodes)

    vector_retriever = index.as_retriever(similarity_top_k=HYBRID_TOP_K)
    bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=HYBRID_TOP_K)

    # Phase 3: fuse retrievers with Reciprocal Rank Fusion
    fusion_retriever = QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        similarity_top_k=HYBRID_TOP_K,
        num_queries=1,          # don't generate extra query variants — keeps latency low
        mode="reciprocal_rerank",
        use_async=True,
    )

    # Phase 4: rerank fused candidates down to RERANK_TOP_N
    reranker = LLMRerank(
        choice_batch_size=10,
        top_n=RERANK_TOP_N,
    )

    return RetrieverQueryEngine.from_args(
        retriever=fusion_retriever,
        node_postprocessors=[reranker],
    )


# ---------------------------------------------------------------------------
# Phase 5 – Interactive agent
# ---------------------------------------------------------------------------

async def run_chat() -> None:
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")

    llm = OpenAI(model=LLM_MODEL)

    print_header("\n=== EMR Hybrid Search Agent ===")
    print_faded(f"  LLM model         : {LLM_MODEL}")
    print_faded(f"  Embedding model   : {EMBED_MODEL_ID}")
    print_faded(f"  Search mode       : Hybrid (BM25 + Vector, RRF fusion)")
    print_faded(f"  Reranker          : LLMRerank (top {RERANK_TOP_N} of {HYBRID_TOP_K})")
    print_faded("")

    print_faded("[startup] Configuring medical embeddings…")
    configure_settings(llm)

    print_faded("[startup] Chunking patient files by section…")
    nodes = build_nodes()
    print_faded(f"[startup] {len(nodes)} section-chunks from {len(list(PATIENT_DIR.glob('*.md')))} patient files.")

    print_faded("[startup] Building vector index + BM25 index…")
    query_engine = build_query_engine(nodes, llm)
    print_faded("[startup] Ready.\n")

    # --- Agent tool definitions ---

    async def search_patient_documents(query: str) -> str:
        """
        Search indexed patient section-chunks using hybrid BM25+vector retrieval
        with LLM reranking. Returns relevant findings with citations.
        Each retrieved chunk is tagged [POSITIVE FINDING] or [NEGATIVE / no finding]
        so the agent can correctly handle negations like 'No known allergies'.
        """
        print_faded(f"\n[tool] search_patient_documents(query={query!r})")
        print_faded(f"[tool] Running hybrid retrieval (BM25 + vector, top-{HYBRID_TOP_K} each)…")

        response = await query_engine.aquery(query)
        answer = str(response).strip()
        source_nodes = getattr(response, "source_nodes", []) or []

        print_faded(f"[tool] Reranker surfaced {len(source_nodes)} chunk(s):")
        chunk_lines = []
        citation_lines = []
        for i, node_with_score in enumerate(source_nodes):
            meta = getattr(node_with_score.node, "metadata", {}) or {}
            patient = meta.get("patient_name", "Unknown")
            section = meta.get("section", "?")
            fname = meta.get("file_name", "?")
            has_finding = meta.get("has_finding", True)
            preview = meta.get("content_preview", "")
            score = getattr(node_with_score, "score", None)
            score_str = f"  score={score:.3f}" if score is not None else ""
            finding_flag = "[POSITIVE FINDING]" if has_finding else "[NEGATIVE / no finding]"
            print_faded(f"  [{i+1}] {finding_flag} {fname} § {section}{score_str}")
            citation_lines.append(f"{fname} § {section} ({patient})")
            chunk_lines.append(
                f"{finding_flag} Patient: {patient} | Section: {section}\n  Content: {preview}"
            )

        chunks_summary = "\n".join(chunk_lines)
        tool_result = (
            f"{answer}\n\n"
            f"--- Retrieved chunks (use [POSITIVE FINDING] / [NEGATIVE] flags to filter) ---\n"
            f"{chunks_summary}\n\n"
            f"Sources:\n" + "\n".join(f"  • {c}" for c in sorted(set(citation_lines)))
        )

        print_faded(f"[tool result]\n{tool_result}\n")
        return tool_result


    def count_patient_documents() -> int:
        """Return the number of indexed patient files."""
        n = len(list(PATIENT_DIR.glob("*.md")))
        print_faded(f"[tool] count_patient_documents() -> {n}")
        return n

    def scan_all_patients(keyword: str, section_filter: str = "") -> str:
        """
        Exhaustive full-scan of ALL patient section-chunks for a keyword.
        Use this instead of search_patient_documents when the user asks:
        - 'list ALL patients who...' / 'show ALL patients with...'
        - questions about demographics (location, age, sex, ethnicity)
        - questions where completeness matters more than ranking

        Unlike search_patient_documents, this has NO top-K cap and returns
        every chunk that contains the keyword in its embedded text.

        Args:
            keyword: word or phrase to scan for (case-insensitive)
            section_filter: if provided, only scan chunks from this section
                           (e.g. 'Patient', 'Social History', 'Problem List')
        """
        print_faded(f"\n[tool] scan_all_patients(keyword={keyword!r}, section_filter={section_filter!r})")
        kw = keyword.lower()
        section_f = section_filter.lower()

        matches = []
        seen_patients = set()
        for node in nodes:
            meta = node.metadata
            section = meta.get("section", "")
            if section_f and section_f not in section.lower():
                continue
            text_lower = node.text.lower()
            if kw in text_lower:
                patient = meta.get("patient_name", "?")
                fname = meta.get("file_name", "?")
                preview = meta.get("content_preview", node.text[:80])
                key = (patient, section)
                if key not in seen_patients:
                    seen_patients.add(key)
                    matches.append(f"• {patient} ({fname} § {section}): {preview}")

        print_faded(f"[tool] scan found {len(matches)} matching chunk(s)")
        if not matches:
            return f"No patients found matching keyword '{keyword}'" + (
                f" in section '{section_filter}'" if section_filter else ""
            )
        return (
            f"Found {len(matches)} match(es) for '{keyword}':\n" +
            "\n".join(matches)
        )

    async def extract_and_chart(
        patient_name: str,
        metric: str,
        chart_type: str = "line",
    ) -> str:
        """
        Extract a clinical metric over time from encounter notes and generate a chart.

        Use this when the user asks to chart or graph a value like:
        "chart A1C for Harpreet Dhillon over the last 2 years"
        "plot blood pressure readings for Maya Chen"
        "show weight trend for Lucas McLeod"

        Steps:
          1. Scans all encounter nodes for the patient + metric keyword
          2. Sends the text to GPT-4o to extract {date, value, unit} triples as JSON
          3. Renders a matplotlib chart (line or bar) and saves it as a PNG
          4. Returns the absolute path to the PNG so the user can open it

        Args:
            patient_name: full or partial name (case-insensitive)
            metric: the clinical value to extract (e.g. 'A1C', 'HbA1c', 'blood pressure',
                    'weight', 'BMI', 'fasting glucose', 'LDL', 'eGFR')
            chart_type: 'line' (default) or 'bar'
        """
        print_faded(f"\n[tool] extract_and_chart(patient={patient_name!r}, metric={metric!r})")

        # -- Step 1: collect all encounter chunks containing the metric for this patient --
        name_lower = patient_name.lower()
        metric_lower = metric.lower()
        relevant_chunks = []
        for node in nodes:
            meta = node.metadata
            if meta.get("document_type") != "encounter":
                continue
            if name_lower not in meta.get("patient_name", "").lower():
                continue
            if metric_lower not in node.text.lower():
                continue
            relevant_chunks.append(
                f"[Date: {meta.get('encounter_date','?')} | Visit: {meta.get('encounter_reason','?')}]\n"
                f"{meta.get('content_preview', node.text[:300])}"
            )

        if not relevant_chunks:
            return (
                f"No encounter notes found for '{patient_name}' containing '{metric}'. "
                f"Try a different metric name or check the patient name spelling."
            )

        print_faded(f"[tool] Found {len(relevant_chunks)} chunk(s) with '{metric}' for {patient_name}")

        # -- Step 2: ask GPT-4o to extract structured {date, value, unit} triples --
        chunks_text = "\n\n".join(relevant_chunks[:20])  # cap at 20 chunks to stay within context
        extraction_prompt = (
            f"From the following clinical encounter notes for patient '{patient_name}', "
            f"extract every recorded value of '{metric}'.\n"
            f"Return ONLY a JSON array of objects with keys: \"date\" (YYYY-MM-DD), "
            f"\"value\" (numeric), \"unit\" (string). "
            f"If a date is approximate, use your best estimate. "
            f"Omit entries where the value is not numeric. "
            f"Return [] if none found.\n\n"
            f"NOTES:\n{chunks_text}"
        )

        extract_response = await llm.acomplete(extraction_prompt)
        raw_json = str(extract_response).strip()

        # Strip markdown code fences if present
        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
        raw_json = re.sub(r"```\s*$", "", raw_json, flags=re.MULTILINE).strip()

        try:
            data_points = json.loads(raw_json)
        except json.JSONDecodeError:
            return (
                f"Extracted text from encounters but could not parse structured values for '{metric}'. "
                f"Raw extraction:\n{raw_json[:500]}"
            )

        if not data_points:
            return f"No numeric values for '{metric}' found in {patient_name}'s encounter notes."

        print_faded(f"[tool] Extracted {len(data_points)} data point(s): {data_points}")

        # -- Step 3: render chart --
        try:
            dates = [datetime.strptime(p["date"], "%Y-%m-%d") for p in data_points]
            values = [float(p["value"]) for p in data_points]
            units = data_points[0].get("unit", "") if data_points else ""

            # Sort by date
            pairs = sorted(zip(dates, values), key=lambda x: x[0])
            dates, values = zip(*pairs) if pairs else ([], [])

            fig, ax = plt.subplots(figsize=(10, 5))
            if chart_type == "bar":
                ax.bar([d.strftime("%Y-%m-%d") for d in dates], values,
                       color="steelblue", edgecolor="white")
                ax.set_xticks(range(len(dates)))
                ax.set_xticklabels([d.strftime("%Y-%m-%d") for d in dates],
                                   rotation=30, ha="right")
            else:  # line (default)
                ax.plot(dates, values, marker="o", linewidth=2,
                        color="steelblue", markersize=7, markerfacecolor="white",
                        markeredgewidth=2)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                fig.autofmt_xdate(rotation=30)

            ax.set_title(f"{metric} — {patient_name}", fontsize=14, fontweight="bold")
            ax.set_xlabel("Date")
            ylabel = f"{metric} ({units})" if units else metric
            ax.set_ylabel(ylabel)
            ax.grid(True, linestyle="--", alpha=0.5)
            fig.tight_layout()

            # Save to a temp file in the project root's charts/ directory
            charts_dir = PROJECT_ROOT / "charts"
            charts_dir.mkdir(exist_ok=True)
            safe_name = re.sub(r"[^\w\s-]", "", f"{patient_name}_{metric}").replace(" ", "_")
            chart_path = charts_dir / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            fig.savefig(chart_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

            print_faded(f"[tool] Chart saved to {chart_path}")
            return (
                f"Chart generated for {patient_name} — {metric}\n"
                f"Data points ({len(data_points)}): "
                + ", ".join(f"{d.strftime('%Y-%m-%d')}: {v} {units}" for d, v in zip(dates, values))
                + f"\n\nChart saved to: {chart_path}\n"
                f"Open the file to view the chart."
            )

        except Exception as e:
            return f"Chart generation failed: {e}. Data extracted: {data_points}"

    agent = FunctionAgent(
        tools=[search_patient_documents, scan_all_patients, extract_and_chart, count_patient_documents],
        llm=llm,
        system_prompt=(
            "You are a clinical document assistant for an EMR system. "
            "You have access to three search/analysis tools:\n"
            "1. search_patient_documents(query) — hybrid semantic+BM25 search with reranking. "
            "Best for clinical questions (diagnoses, medications, treatments, assessments) "
            "across BOTH the patient IPS summaries AND historical encounter SOAP notes. "
            "Returns at most 4 ranked results.\n"
            "2. scan_all_patients(keyword, section_filter) — exhaustive full-scan with NO result cap. "
            "Use this whenever the user asks to list ALL patients, or asks about demographics "
            "(location, age, sex, ethnicity). For location queries use section_filter='Patient'.\n"
            "3. extract_and_chart(patient_name, metric, chart_type) — extracts a clinical metric "
            "(e.g. 'A1C', 'blood pressure', 'weight', 'BMI', 'LDL') over time from encounter notes "
            "and generates a PNG chart. Use this whenever the user asks to chart, graph, plot, "
            "or visualise a trend for a specific patient.\n\n"
            "ENCOUNTER DATA: The index includes both IPS patient summaries AND encounter SOAP notes "
            "(Subjective, Objective, Assessment, Plan) from multiple visits per patient. "
            "For questions about a specific visit, what happened at an appointment, or longitudinal "
            "trends — search the encounter notes.\n\n"
            "CRITICAL NEGATION RULE: search_patient_documents returns chunks tagged "
            "[POSITIVE FINDING] or [NEGATIVE / no finding]. "
            "When a user asks 'which patients have X', ONLY count [POSITIVE FINDING] chunks "
            "whose content actually describes X. "
            "A chunk saying 'No known allergies' means the patient does NOT have the condition.\n\n"
            "When citing evidence always mention the patient name, document section, encounter date "
            "(if from an encounter note), and file name. If you are unsure, say so."
        ),
    )


    ctx = Context(agent)

    n_patients = len(list(PATIENT_DIR.glob("*.md")))
    n_encounters = sum(1 for p in ENCOUNTER_DIR.glob("*.md")) if ENCOUNTER_DIR.exists() else 0
    print_header(f"Patient agent ready — {n_patients} patients | {n_encounters} encounter files | {len(nodes)} indexed chunks.")
    print("Type your question or 'exit' to quit.\n")

    while True:
        try:
            user_msg = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_msg:
            continue
        readline.add_history(user_msg)
        if user_msg.lower() in {"exit", "quit"}:
            break

        response = await agent.run(user_msg=user_msg, ctx=ctx)
        print(f"\nAgent> {response}\n")


if __name__ == "__main__":
    asyncio.run(run_chat())

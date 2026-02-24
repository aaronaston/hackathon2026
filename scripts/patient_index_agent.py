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
import re
import os
from pathlib import Path
import readline

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
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"

# ----- Models ---------------------------------------------------------------
LLM_MODEL = "gpt-4o"
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

        node_meta = {
            **shared_meta,
            "section": section,
            "has_finding": has_finding,
            "content_preview": content_body[:120],
        }
        nodes.append(TextNode(text=embed_text, metadata=node_meta))

    return nodes



def build_nodes() -> list[TextNode]:
    """Build all section-level TextNodes from every patient markdown file."""
    all_nodes: list[TextNode] = []
    for path in sorted(PATIENT_DIR.glob("*.md")):
        all_nodes.extend(chunk_patient_file(path))
    if not all_nodes:
        raise RuntimeError(f"No patient markdown files found in {PATIENT_DIR}")
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

    agent = FunctionAgent(
        tools=[search_patient_documents, count_patient_documents],
        llm=llm,
        system_prompt=(
            "You are a clinical document assistant for an EMR system. "
            "Use the search_patient_documents tool to answer questions about patients. "
            "\n\nCRITICAL NEGATION RULE: The tool returns chunks tagged as either "
            "[POSITIVE FINDING] or [NEGATIVE / no finding]. "
            "When a user asks 'which patients have X', you MUST ONLY count patients whose chunk "
            "is tagged [POSITIVE FINDING] and whose content actually describes X. "
            "A chunk saying 'No known allergies' or 'No known drug allergies' is a NEGATIVE — "
            "it means the patient does NOT have the condition. Never list such patients as having the condition. "
            "\n\nWhen citing evidence always mention the patient name, the document section, and file name. "
            "If you are unsure, say so — do not invent patient information."
        ),
    )

    ctx = Context(agent)

    n_patients = count_patient_documents()
    print_header(f"Patient agent ready — {n_patients} patients indexed.")
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

#!/usr/bin/env python3
"""Interactive patient document agent (in-memory index, no persistence)."""

import asyncio
from pathlib import Path
import readline

from llama_index.core import VectorStoreIndex
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.schema import TextNode
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"
MODEL = "gpt-5.1"


readline.parse_and_bind("tab: complete")
readline.parse_and_bind("set editing-mode emacs")


def print_faded(text: str) -> None:
    """Print tool/debug output in dim gray text."""
    print(f"\033[90m{text}\033[0m", flush=True)


def build_index() -> VectorStoreIndex:
    """Build an in-memory vector index with one node per patient file."""
    nodes = []
    for path in sorted(PATIENT_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        nodes.append(
            TextNode(
                text=text,
                metadata={
                    "file_name": path.name,
                    "file_path": str(path.relative_to(PROJECT_ROOT)),
                },
            )
        )

    if not nodes:
        raise RuntimeError(f"No patient markdown files found in {PATIENT_DIR}")

    return VectorStoreIndex(nodes=nodes)


async def run_chat() -> None:
    index = build_index()
    query_engine = index.as_query_engine(similarity_top_k=4)

    async def search_patient_documents(query: str) -> str:
        """Search indexed patient summaries and return relevant findings with citations."""
        print_faded(f"[tool] search_patient_documents(query={query!r})")
        response = await query_engine.aquery(query)
        answer = str(response).strip()
        source_nodes = getattr(response, "source_nodes", []) or []

        citations = []
        for node_with_score in source_nodes:
            metadata = getattr(node_with_score.node, "metadata", {}) or {}
            file_path = metadata.get("file_path")
            if file_path:
                citations.append(str((PROJECT_ROOT / file_path).resolve()))
                continue

            file_name = metadata.get("file_name")
            if file_name:
                citations.append(str((PATIENT_DIR / file_name).resolve()))

        unique_citations = sorted(set(citations))
        if unique_citations:
            tool_result = f"{answer}\n\nSources: {', '.join(unique_citations)}"
        else:
            tool_result = answer

        print_faded(f"[tool result] {tool_result}")
        return tool_result

    def count_patient_documents() -> int:
        """Return the number of indexed patient summaries."""
        result = len(list(PATIENT_DIR.glob("*.md")))
        print_faded(f"[tool] count_patient_documents() -> {result}")
        return result

    llm = OpenAI(model=MODEL)
    agent = FunctionAgent(
        tools=[search_patient_documents, count_patient_documents],
        llm=llm,
        system_prompt=(
            "You are a clinical document assistant. "
            "Use the search_patient_documents tool for patient-specific questions. "
            "When citing evidence, include the file_name from metadata when available."
        ),
    )

    # Keep this context object for the whole process to maintain chat history.
    ctx = Context(agent)

    print("Patient agent ready. Type questions, or 'exit' to quit.")
    print(f"Indexed {count_patient_documents()} patient files from {PATIENT_DIR}.")

    while True:
        user_msg = input("\nYou> ").strip()
        if not user_msg:
            continue
        readline.add_history(user_msg)
        if user_msg.lower() in {"exit", "quit"}:
            break

        response = await agent.run(user_msg=user_msg, ctx=ctx)
        print(f"\nAgent> {response}")


if __name__ == "__main__":
    asyncio.run(run_chat())

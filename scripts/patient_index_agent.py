#!/usr/bin/env python3
"""Interactive patient document agent (in-memory index, no persistence)."""

import argparse
import asyncio
from pathlib import Path
import readline
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"
MODEL = "gpt-5.1"


readline.parse_and_bind("tab: complete")
readline.parse_and_bind("set editing-mode emacs")


def print_faded(text: str) -> None:
    """Print tool/debug output with a clear prefix for terminal readability."""
    print(f"[tool] {text}", flush=True)


def find_patients_with_allergy_term(allergy_term: str) -> list[str]:
    """Return patient file names whose allergy section contains the given term."""
    term = allergy_term.strip()
    if not term:
        return []

    pattern = re.compile(re.escape(term), flags=re.IGNORECASE)
    matches = []

    for path in sorted(PATIENT_DIR.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        in_allergies = False

        for line in lines:
            if line.startswith("## "):
                in_allergies = line.startswith("## Allergies and Intolerances")
                continue

            if not in_allergies:
                continue

            if pattern.search(line):
                matches.append(path.name)
                break

    return matches


def build_index():
    """Build an in-memory vector index with one node per patient file."""
    from llama_index.core import VectorStoreIndex
    from llama_index.core.schema import TextNode

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
    from llama_index.core.agent.workflow import FunctionAgent
    from llama_index.core.workflow import Context
    from llama_index.llms.openai import OpenAI

    index = build_index()
    query_engine = index.as_query_engine(similarity_top_k=8)

    async def search_patient_documents(query: str) -> str:
        """Search indexed patient summaries and return relevant findings with citations."""
        print_faded(f"search_patient_documents(query={query!r})")
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

        print_faded(f"search result:\n{tool_result}")
        return tool_result

    def count_patients_with_allergy(allergy_term: str) -> str:
        """Count patients whose allergy section contains the given term."""
        term = allergy_term.strip()
        if not term:
            return "allergy_term is empty. Provide a term such as 'peanut'."
        matches = find_patients_with_allergy_term(term)

        result = (
            f"Found {len(matches)} patient(s) with allergy term '{term}'. "
            f"Matches: {', '.join(matches) if matches else 'none'}"
        )
        print_faded(f"count_patients_with_allergy(allergy_term={term!r}) -> {result}")
        return result

    def count_patient_documents() -> int:
        """Return the number of indexed patient summaries."""
        result = len(list(PATIENT_DIR.glob("*.md")))
        print_faded(f"count_patient_documents() -> {result}")
        return result

    llm = OpenAI(model=MODEL)
    agent = FunctionAgent(
        tools=[
            search_patient_documents,
            count_patient_documents,
            count_patients_with_allergy,
        ],
        llm=llm,
        system_prompt=(
            "You are a clinical document assistant. "
            "For counting allergy terms, always use count_patients_with_allergy first. "
            "Use search_patient_documents for patient-specific or free-text questions. "
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patient document retrieval/count tool")
    parser.add_argument(
        "--count-allergy",
        metavar="TERM",
        help="Count patients whose allergy section contains TERM, without starting the LLM agent.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count_allergy:
        matches = find_patients_with_allergy_term(args.count_allergy)
        print(
            f"Found {len(matches)} patient(s) with allergy term '{args.count_allergy}': "
            f"{', '.join(matches) if matches else 'none'}"
        )
        return

    asyncio.run(run_chat())


if __name__ == "__main__":
    main()

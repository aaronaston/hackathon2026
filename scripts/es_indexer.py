#!/usr/bin/env python3
"""Elasticsearch indexer for patient keyword search.

Indexes patient data into Elasticsearch with three buckets:
- first_name: Patient first name (prefix searchable)
- last_name: Patient last name (prefix searchable)
- health_number: Synthetic health number (prefix searchable)

Usage:
    python scripts/es_indexer.py           # Reindex all patients
    python scripts/es_indexer.py --clear   # Clear index and reindex
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"

ES_HOST = "http://localhost:9200"
ES_INDEX = "patients_keyword"


def generate_health_number(patient_id: str, name: str) -> str:
    """Generate a synthetic Ontario Health Number (10 digits) from patient data."""
    # Create a deterministic hash from patient ID and name
    seed = f"{patient_id}:{name}".encode()
    hash_digest = hashlib.sha256(seed).hexdigest()
    # Take first 10 digits (with leading digit 1-9 for realism)
    numeric = "".join(c for c in hash_digest if c.isdigit())[:10]
    if len(numeric) < 10:
        numeric = numeric.ljust(10, "0")
    # Ensure first digit is 1-9
    if numeric[0] == "0":
        numeric = "1" + numeric[1:]
    return numeric


def parse_patient_file(path: Path) -> dict:
    """Parse a patient markdown file and extract name fields."""
    lines = path.read_text(encoding="utf-8").splitlines()

    patient_meta = {}
    in_patient = False

    for line in lines:
        line = line.rstrip()

        if line.startswith("## "):
            heading = line.replace("## ", "", 1).strip().lower()
            in_patient = heading == "patient"
            continue

        if line.startswith("- ") and in_patient and ":" in line:
            bullet = line[2:].strip()
            k, v = bullet.split(":", 1)
            patient_meta[k.strip().lower()] = v.strip()

    name = patient_meta.get("name", path.stem)
    patient_id = path.stem

    # Split name into first and last
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    health_number = generate_health_number(patient_id, name)

    return {
        "patient_id": patient_id,
        "full_name": name,
        "first_name": first_name,
        "last_name": last_name,
        "health_number": health_number,
    }


def create_index(es: Elasticsearch) -> None:
    """Create the Elasticsearch index with appropriate mappings."""
    # Use keyword type with normalizer for case-insensitive prefix search
    index_settings = {
        "settings": {
            "analysis": {
                "normalizer": {
                    "lowercase_normalizer": {
                        "type": "custom",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "patient_id": {"type": "keyword"},
                "full_name": {"type": "text"},
                "first_name": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "last_name": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "health_number": {
                    "type": "keyword"
                }
            }
        }
    }

    if es.indices.exists(index=ES_INDEX):
        print(f"Index '{ES_INDEX}' already exists")
        return

    es.indices.create(index=ES_INDEX, body=index_settings)
    print(f"Created index '{ES_INDEX}'")


def clear_index(es: Elasticsearch) -> None:
    """Delete and recreate the index."""
    if es.indices.exists(index=ES_INDEX):
        es.indices.delete(index=ES_INDEX)
        print(f"Deleted index '{ES_INDEX}'")
    create_index(es)


def index_patients(es: Elasticsearch) -> int:
    """Index all patient files into Elasticsearch."""
    patient_files = sorted(PATIENT_DIR.glob("*.md"))

    if not patient_files:
        print(f"No patient files found in {PATIENT_DIR}")
        return 0

    def generate_actions():
        for path in patient_files:
            patient = parse_patient_file(path)
            yield {
                "_index": ES_INDEX,
                "_id": patient["patient_id"],
                "_source": patient
            }

    success, errors = bulk(es, generate_actions(), raise_on_error=False)

    if errors:
        print(f"Indexing errors: {errors}")

    return success


def prefix_search(es: Elasticsearch, query: str, min_chars: int = 2) -> dict:
    """
    Search for prefix matches across first_name, last_name, and health_number.

    Returns:
        {
            "bucket": str or None,  # "first_name", "last_name", "health_number", or None if multi-bucket
            "results": list[dict],  # Matching patients
            "multi_bucket": bool    # True if matches span multiple buckets
        }
    """
    if len(query) < min_chars:
        return {"bucket": None, "results": [], "multi_bucket": False}

    query_lower = query.lower()

    # Build prefix queries for each bucket
    search_body = {
        "size": 50,  # Get more than we need to check bucket distribution
        "query": {
            "bool": {
                "should": [
                    {"prefix": {"first_name": {"value": query_lower}}},
                    {"prefix": {"last_name": {"value": query_lower}}},
                    {"prefix": {"health_number": {"value": query}}}  # Health numbers are case-sensitive
                ],
                "minimum_should_match": 1
            }
        }
    }

    response = es.search(index=ES_INDEX, body=search_body)
    hits = response.get("hits", {}).get("hits", [])

    if not hits:
        return {"bucket": None, "results": [], "multi_bucket": False}

    # Determine which bucket each hit matched
    results = []
    bucket_counts = {"first_name": 0, "last_name": 0, "health_number": 0}

    for hit in hits:
        source = hit["_source"]
        matched_buckets = []

        if source.get("first_name", "").lower().startswith(query_lower):
            matched_buckets.append("first_name")
            bucket_counts["first_name"] += 1
        if source.get("last_name", "").lower().startswith(query_lower):
            matched_buckets.append("last_name")
            bucket_counts["last_name"] += 1
        if source.get("health_number", "").startswith(query):
            matched_buckets.append("health_number")
            bucket_counts["health_number"] += 1

        results.append({
            "patient_id": source["patient_id"],
            "full_name": source["full_name"],
            "first_name": source["first_name"],
            "last_name": source["last_name"],
            "health_number": source["health_number"],
            "matched_buckets": matched_buckets
        })

    # Determine if all matches are from the same bucket
    non_empty_buckets = [k for k, v in bucket_counts.items() if v > 0]

    if len(non_empty_buckets) == 0:
        return {"bucket": None, "results": [], "multi_bucket": False}
    elif len(non_empty_buckets) == 1:
        return {
            "bucket": non_empty_buckets[0],
            "results": results,
            "multi_bucket": False
        }
    else:
        return {
            "bucket": None,
            "results": results,
            "multi_bucket": True
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Index patients into Elasticsearch")
    parser.add_argument("--clear", action="store_true", help="Clear index before reindexing")
    parser.add_argument("--test", type=str, help="Test prefix search with given query")
    args = parser.parse_args()

    try:
        es = Elasticsearch([ES_HOST])
        if not es.ping():
            print(f"Cannot connect to Elasticsearch at {ES_HOST}")
            print("Make sure Elasticsearch is running: docker-compose up -d")
            sys.exit(1)
    except Exception as e:
        print(f"Elasticsearch connection error: {e}")
        print("Make sure Elasticsearch is running: docker-compose up -d")
        sys.exit(1)

    if args.test:
        result = prefix_search(es, args.test)
        print(f"Search for '{args.test}':")
        print(f"  Bucket: {result['bucket']}")
        print(f"  Multi-bucket: {result['multi_bucket']}")
        print(f"  Results ({len(result['results'])}):")
        for r in result["results"][:10]:
            print(f"    - {r['full_name']} (HN: {r['health_number']}) [{', '.join(r['matched_buckets'])}]")
        return

    if args.clear:
        clear_index(es)
    else:
        create_index(es)

    count = index_patients(es)
    print(f"Indexed {count} patients into Elasticsearch")

    # Verify with a sample search
    print("\nSample searches:")
    for query in ["Lu", "McL", "12"]:
        result = prefix_search(es, query)
        print(f"  '{query}': {len(result['results'])} results, bucket={result['bucket']}, multi={result['multi_bucket']}")


if __name__ == "__main__":
    main()

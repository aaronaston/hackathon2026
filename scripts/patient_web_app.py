#!/usr/bin/env python3
"""Serve a local patient explorer web app and JSON APIs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"
WEB_DIR = PROJECT_ROOT / "web"


SECTION_KEY_MAP = {
    "problem list (required)": "problem_list",
    "allergies and intolerances (required)": "allergies",
    "medication summary (required)": "medications",
    "immunizations": "immunizations",
    "diagnostic results": "diagnostic_results",
    "history of procedures": "procedures",
    "social history": "social_history",
    "vital signs": "vital_signs",
    "plan of care": "plan_of_care",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def parse_address(address: str) -> dict[str, str]:
    # Expected format: "street, city, ON A1A 1A1"
    location = {
        "street": "",
        "city": "",
        "province": "",
        "postal_code": "",
        "country": "Canada",
    }

    raw_parts = [p.strip() for p in address.split(",")]
    if raw_parts:
        location["street"] = raw_parts[0]
    if len(raw_parts) >= 2:
        location["city"] = raw_parts[1]

    tail = raw_parts[-1] if raw_parts else ""
    m = re.search(r"\b([A-Z]{2})\s+([A-Z]\d[A-Z]\s*\d[A-Z]\d)\b", tail)
    if m:
        location["province"] = m.group(1)
        location["postal_code"] = re.sub(r"\s+", "", m.group(2))

    return location


def parse_age_from_dob_line(dob_line_value: str) -> int | None:
    m = re.search(r"\(Age\s+(\d+)\s+as\s+of\s+\d{4}-\d{2}-\d{2}\)", dob_line_value)
    if m:
        return int(m.group(1))
    return None


def parse_patient_file(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()

    patient_meta: dict[str, str] = {}
    sections: dict[str, list[str]] = {v: [] for v in SECTION_KEY_MAP.values()}

    current_section: str | None = None
    for line in lines:
        line = line.rstrip()

        if line.startswith("## "):
            heading = normalize(line.replace("## ", "", 1))
            current_section = SECTION_KEY_MAP.get(heading)
            continue

        if line.startswith("- "):
            bullet = line[2:].strip()
            if current_section in sections:
                sections[current_section].append(bullet)

    # Recover patient metadata by scanning bullet lines under Patient heading.
    # Some parsers set current_section to None for "## Patient" because it is not in SECTION_KEY_MAP.
    in_patient = False
    for line in lines:
        if line.startswith("## "):
            in_patient = normalize(line.replace("## ", "", 1)) == "patient"
            continue
        if in_patient and line.startswith("- ") and ":" in line:
            k, v = line[2:].split(":", 1)
            patient_meta[k.strip().lower()] = v.strip()

    name = patient_meta.get("name", path.stem)
    sex_gender = patient_meta.get("sex/gender", "")
    dob_line = patient_meta.get("date of birth", "")
    dob = dob_line.split("(")[0].strip() if dob_line else ""
    age = parse_age_from_dob_line(dob_line)
    ethnicity = patient_meta.get("ethnicity", "")
    address = patient_meta.get("address", "")
    summary_date = patient_meta.get("summary date", "")

    location = parse_address(address)
    known_allergy = any(
        "no known" not in item.lower() for item in sections.get("allergies", [])
    )

    search_blob = "\n".join(
        [
            name,
            sex_gender,
            ethnicity,
            address,
            "\n".join(sections.get("problem_list", [])),
            "\n".join(sections.get("allergies", [])),
            "\n".join(sections.get("medications", [])),
            "\n".join(sections.get("diagnostic_results", [])),
            "\n".join(sections.get("social_history", [])),
            "\n".join(sections.get("plan_of_care", [])),
        ]
    ).lower()

    return {
        "id": path.stem,
        "file_name": path.name,
        "file_path": str(path.relative_to(PROJECT_ROOT)),
        "name": name,
        "sex_gender": sex_gender,
        "date_of_birth": dob,
        "age": age,
        "ethnicity": ethnicity,
        "address": address,
        "summary_date": summary_date,
        "location": location,
        "known_allergy": known_allergy,
        "sections": sections,
        "search_blob": search_blob,
    }


def load_patients() -> list[dict[str, Any]]:
    return [parse_patient_file(p) for p in sorted(PATIENT_DIR.glob("*.md"))]


def facet_counts(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        if not item:
            continue
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


SEMANTIC_HINTS = {
    "heart": ["cardiac", "hypertension", "blood pressure"],
    "sugar": ["diabetes", "prediabetes", "glucose", "a1c"],
    "breathing": ["asthma", "respiratory", "oxygen"],
    "mood": ["anxiety", "depression", "mental health"],
    "allergy": ["allergies", "intolerance", "rash", "hives"],
    "kidney": ["creatinine", "renal"],
    "pain": ["migraine", "back pain", "osteoarthritis"],
    "cholesterol": ["lipid", "dyslipidemia", "ldl", "statin"],
}


def semantic_tokens(query: str) -> list[str]:
    base = [t for t in re.split(r"[^a-zA-Z0-9]+", query.lower()) if t]
    expanded = set(base)
    for token in base:
        expanded.update(SEMANTIC_HINTS.get(token, []))
    return list(expanded)


def score_patient(patient: dict[str, Any], query: str) -> tuple[int, list[str]]:
    q = query.strip().lower()
    if not q:
        return (0, [])

    tokens = semantic_tokens(q)
    fields = {
        "name": patient.get("name", "").lower(),
        "problems": "\n".join(patient["sections"].get("problem_list", [])).lower(),
        "allergies": "\n".join(patient["sections"].get("allergies", [])).lower(),
        "medications": "\n".join(patient["sections"].get("medications", [])).lower(),
        "location": f"{patient.get('address', '')} {patient.get('ethnicity', '')} {patient.get('sex_gender', '')}".lower(),
        "other": patient.get("search_blob", "").lower(),
    }

    score = 0
    matched: set[str] = set()

    if q in fields["other"]:
        score += 12

    for token in tokens:
        if token in fields["name"]:
            score += 12
            matched.add("name")
        if token in fields["problems"]:
            score += 8
            matched.add("problem list")
        if token in fields["allergies"]:
            score += 8
            matched.add("allergies")
        if token in fields["medications"]:
            score += 7
            matched.add("medications")
        if token in fields["location"]:
            score += 5
            matched.add("profile")
        if token in fields["other"]:
            score += 1

    return score, sorted(matched)


def filter_patients(patients: list[dict[str, Any]], query: dict[str, list[str]]) -> list[dict[str, Any]]:
    text = (query.get("q", [""])[0] or "").strip()
    city = (query.get("city", [""])[0] or "").strip()
    sex_gender = (query.get("sex_gender", [""])[0] or "").strip()
    ethnicity = (query.get("ethnicity", [""])[0] or "").strip()
    allergy = (query.get("known_allergy", ["all"])[0] or "all").strip().lower()

    filtered: list[dict[str, Any]] = []
    for p in patients:
        if city and p["location"].get("city") != city:
            continue
        if sex_gender and p.get("sex_gender") != sex_gender:
            continue
        if ethnicity and p.get("ethnicity") != ethnicity:
            continue
        if allergy == "yes" and not p.get("known_allergy"):
            continue
        if allergy == "no" and p.get("known_allergy"):
            continue

        score, matched = score_patient(p, text)
        if text and score == 0:
            continue

        p2 = dict(p)
        p2["search_score"] = score
        p2["matched_fields"] = matched
        filtered.append(p2)

    if text:
        filtered.sort(key=lambda x: (-x.get("search_score", 0), x.get("name", "")))
    else:
        filtered.sort(key=lambda x: x.get("name", ""))

    return filtered


@dataclass
class AppState:
    patients: list[dict[str, Any]]

    def summary(self) -> dict[str, Any]:
        known_allergy_count = sum(1 for p in self.patients if p.get("known_allergy"))
        return {
            "total_patients": len(self.patients),
            "known_allergy_count": known_allergy_count,
            "city_counts": facet_counts([p["location"].get("city", "") for p in self.patients]),
            "sex_gender_counts": facet_counts([p.get("sex_gender", "") for p in self.patients]),
            "ethnicity_counts": facet_counts([p.get("ethnicity", "") for p in self.patients]),
        }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str | None = None, state: AppState | None = None, **kwargs: Any) -> None:
        self.state = state
        super().__init__(*args, directory=directory, **kwargs)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route == "/api/patients":
            if self.state is None:
                self._send_json({"error": "state unavailable"}, 500)
                return

            results = filter_patients(self.state.patients, query)
            self._send_json({
                "count": len(results),
                "results": results,
            })
            return

        if route == "/api/summary":
            if self.state is None:
                self._send_json({"error": "state unavailable"}, 500)
                return
            self._send_json(self.state.summary())
            return

        super().do_GET()


def build_handler(state: AppState):
    def _handler(*args: Any, **kwargs: Any) -> Handler:
        return Handler(*args, directory=str(WEB_DIR), state=state, **kwargs)

    return _handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve patient explorer web app")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    patients = load_patients()
    state = AppState(patients=patients)
    server = ThreadingHTTPServer((args.host, args.port), build_handler(state))

    print(f"Patient explorer running at http://{args.host}:{args.port}")
    print(f"Loaded {len(patients)} patient records from {PATIENT_DIR}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

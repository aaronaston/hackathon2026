#!/usr/bin/env python3
"""Serve a local patient explorer web app and JSON APIs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATIENT_DIR = PROJECT_ROOT / "test-data" / "patients"
ENCOUNTER_DIR = PROJECT_ROOT / "test-data" / "encounters"
ORGANIZATION_FILE = PROJECT_ROOT / "test-data" / "organizations" / "organizations.md"
PRACTITIONER_FILE = PROJECT_ROOT / "test-data" / "practitioners" / "practitioners.md"
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


SEMANTIC_HINTS = {
    "heart": ["cardiac", "hypertension", "blood pressure", "cardiology"],
    "sugar": ["diabetes", "prediabetes", "glucose", "a1c", "endocrine"],
    "breathing": ["asthma", "respiratory", "oxygen", "respirology"],
    "mood": ["anxiety", "depression", "mental health", "psychiatry"],
    "allergy": ["allergies", "intolerance", "rash", "hives", "anaphylaxis"],
    "kidney": ["creatinine", "renal", "nephrology"],
    "pain": ["migraine", "back pain", "osteoarthritis", "orthopedic"],
    "cholesterol": ["lipid", "dyslipidemia", "ldl", "statin"],
    "child": ["well-child", "pediatric", "immunizations"],
    "senior": ["geriatric", "cognitive", "falls"],
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def parse_address(address: str) -> dict[str, str]:
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


def summarize_text(text: str, max_sentences: int = 2, max_chars: int = 380) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    summary = " ".join(sentences[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary


def extract_key_lines(section_text: str, max_items: int = 3) -> list[str]:
    lines = [ln.strip() for ln in section_text.splitlines() if ln.strip()]
    out: list[str] = []
    for line in lines:
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif ":" in line and len(line) < 180:
            out.append(line)
        if len(out) >= max_items:
            break
    return out


def parse_patient_file(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()

    patient_meta: dict[str, str] = {}
    sections: dict[str, list[str]] = {v: [] for v in SECTION_KEY_MAP.values()}

    current_section: str | None = None
    in_patient = False

    for line in lines:
        line = line.rstrip()

        if line.startswith("## "):
            heading = normalize(line.replace("## ", "", 1))
            current_section = SECTION_KEY_MAP.get(heading)
            in_patient = heading == "patient"
            continue

        if line.startswith("- "):
            bullet = line[2:].strip()
            if in_patient and ":" in bullet:
                k, v = bullet.split(":", 1)
                patient_meta[k.strip().lower()] = v.strip()
                continue
            if current_section in sections:
                sections[current_section].append(bullet)

    name = patient_meta.get("name", path.stem)
    sex_gender = patient_meta.get("sex/gender", "")
    dob_line = patient_meta.get("date of birth", "")
    dob = dob_line.split("(")[0].strip() if dob_line else ""
    age = parse_age_from_dob_line(dob_line)
    ethnicity = patient_meta.get("ethnicity", "")
    address = patient_meta.get("address", "")
    summary_date = patient_meta.get("summary date", "")

    location = parse_address(address)
    known_allergy = any("no known" not in item.lower() for item in sections.get("allergies", []))

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
    }


def parse_encounter_file(path: Path) -> tuple[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    patient_name = path.stem
    header_match = re.search(r"^#\s+Encounters:\s*(.+)$", text, flags=re.MULTILINE)
    if header_match:
        patient_name = header_match.group(1).strip()

    encounter_indexes = [idx for idx, line in enumerate(lines) if line.startswith("## Encounter ")]
    encounters: list[dict[str, Any]] = []

    for n, start_idx in enumerate(encounter_indexes):
        end_idx = encounter_indexes[n + 1] if n + 1 < len(encounter_indexes) else len(lines)
        block_lines = lines[start_idx:end_idx]
        title_line = block_lines[0]

        date_str = ""
        title = title_line.replace("## ", "", 1).strip()
        m = re.match(r"##\s+Encounter\s+\d+:\s*(\d{4}-\d{2}-\d{2})\s+[—-]\s*(.+)", title_line)
        if m:
            date_str = m.group(1)
            title = m.group(2).strip()

        metadata: dict[str, str] = {}
        sections: dict[str, str] = {}
        current_section: str | None = None
        section_buffer: list[str] = []

        for line in block_lines[1:]:
            if line.startswith("### "):
                if current_section is not None:
                    sections[current_section] = "\n".join(section_buffer).strip()
                current_section = normalize(line.replace("### ", "", 1))
                section_buffer = []
                continue

            if current_section is None and line.startswith("- ") and ":" in line:
                k, v = line[2:].split(":", 1)
                metadata[normalize(k)] = v.strip()
                continue

            if current_section is not None:
                section_buffer.append(line)

        if current_section is not None:
            sections[current_section] = "\n".join(section_buffer).strip()

        assessment = sections.get("assessment", "")
        plan = sections.get("plan", "")
        objective = sections.get("objective", "")
        subjective = sections.get("subjective", "")

        summary = {
            "clinical_summary": summarize_text(assessment or plan or subjective, max_sentences=2),
            "assessment_summary": summarize_text(assessment, max_sentences=2),
            "plan_summary": summarize_text(plan, max_sentences=2),
            "subjective_summary": summarize_text(subjective, max_sentences=1),
            "objective_highlights": extract_key_lines(objective, max_items=3),
        }

        encounters.append(
            {
                "encounter_id": f"{path.stem}-{n + 1}",
                "title": title,
                "date": metadata.get("date", date_str),
                "time": metadata.get("time", ""),
                "type": metadata.get("type", ""),
                "setting": metadata.get("setting", ""),
                "organization": metadata.get("organization", ""),
                "practitioner": metadata.get("practitioner", ""),
                "reason_for_visit": metadata.get("reason for visit", ""),
                "sections": sections,
                "summary": summary,
                "source_file": path.name,
                "full_text": "\n".join(block_lines).strip(),
            }
        )

    return patient_name, encounters


def parse_roster_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    section_name = ""
    current_name = ""
    current_data: dict[str, Any] = {}
    entries: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current_name, current_data
        if not current_name:
            return
        item = {"name": current_name, "category": section_name}
        item.update(current_data)
        entries.append(item)
        current_name = ""
        current_data = {}

    for line in lines:
        if line.startswith("## "):
            flush()
            section_name = line.replace("## ", "", 1).strip()
            continue

        if line.startswith("### "):
            flush()
            current_name = line.replace("### ", "", 1).strip()
            current_data = {}
            continue

        if line.startswith("- ") and ":" in line and current_name:
            k, v = line[2:].split(":", 1)
            key = normalize(k)
            value = v.strip()
            if key in {"patients", "affiliated practitioners", "services"}:
                current_data[key] = [p.strip() for p in value.split(",") if p.strip()]
            else:
                current_data[key] = value

    flush()
    return entries


def load_encounters() -> dict[str, list[dict[str, Any]]]:
    by_patient: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(ENCOUNTER_DIR.glob("*.md")):
        patient_name, encounters = parse_encounter_file(path)
        by_patient[patient_name] = encounters
    return by_patient


def load_patients() -> list[dict[str, Any]]:
    return [parse_patient_file(p) for p in sorted(PATIENT_DIR.glob("*.md"))]


def parse_practitioner_name(raw: str) -> str:
    # "Dr. Sarah Mitchell, MD CCFP (ON-PRAC...)" -> "Dr. Sarah Mitchell"
    name = raw.split("(")[0].strip()
    if "," in name:
        name = name.split(",", 1)[0].strip()
    return name


def clean_org_name(raw: str) -> str:
    # "Organization Name (Address)" -> "Organization Name"
    return raw.split("(", 1)[0].strip()


def enrich_patients(
    patients: list[dict[str, Any]],
    encounters_by_patient: dict[str, list[dict[str, Any]]],
    organizations: list[dict[str, Any]],
    practitioners: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    patient_to_practitioners: dict[str, list[str]] = {}
    for practitioner in practitioners:
        normalized_practitioner_name = parse_practitioner_name(practitioner.get("name", ""))
        for patient_name in practitioner.get("patients", []):
            patient_to_practitioners.setdefault(patient_name, []).append(normalized_practitioner_name)

    org_lookup = {o.get("name", ""): o for o in organizations}
    practitioner_lookup = {p.get("name", ""): p for p in practitioners}

    enriched: list[dict[str, Any]] = []
    for patient in patients:
        name = patient.get("name", "")
        encounters = encounters_by_patient.get(name, [])

        encounter_types = sorted({e.get("type", "") for e in encounters if e.get("type")})
        encounter_settings = sorted({e.get("setting", "") for e in encounters if e.get("setting")})
        encounter_org_names = sorted({clean_org_name(e.get("organization", "")) for e in encounters if e.get("organization")})

        encounter_practitioner_names = sorted(
            {
                parse_practitioner_name(e.get("practitioner", ""))
                for e in encounters
                if e.get("practitioner")
            }
        )

        roster_practitioners = sorted(set(patient_to_practitioners.get(name, [])))
        all_practitioners = sorted(set(encounter_practitioner_names + roster_practitioners))

        encounter_dates = [
            parsed
            for parsed in (parse_iso_date(e.get("date", "")) for e in encounters)
            if parsed is not None
        ]
        last_encounter_date = max(encounter_dates).isoformat() if encounter_dates else ""

        org_details = [org_lookup.get(org, {"name": org}) for org in encounter_org_names]
        practitioner_details = [practitioner_lookup.get(pr, {"name": pr}) for pr in all_practitioners]

        sections = patient.get("sections", {})
        search_blob = "\n".join(
            [
                patient.get("name", ""),
                patient.get("sex_gender", ""),
                patient.get("ethnicity", ""),
                patient.get("address", ""),
                "\n".join(sections.get("problem_list", [])),
                "\n".join(sections.get("allergies", [])),
                "\n".join(sections.get("medications", [])),
                "\n".join(sections.get("diagnostic_results", [])),
                "\n".join(sections.get("social_history", [])),
                "\n".join(sections.get("plan_of_care", [])),
                "\n".join(e.get("reason_for_visit", "") for e in encounters),
                "\n".join(e.get("full_text", "") for e in encounters),
                "\n".join(org.get("name", "") for org in org_details),
                "\n".join(pr.get("name", "") for pr in practitioner_details),
            ]
        ).lower()

        out = dict(patient)
        out.update(
            {
                "encounters": encounters,
                "encounter_count": len(encounters),
                "last_encounter_date": last_encounter_date,
                "encounter_types": encounter_types,
                "encounter_settings": encounter_settings,
                "organizations": encounter_org_names,
                "organization_details": org_details,
                "practitioners": all_practitioners,
                "practitioner_details": practitioner_details,
                "search_blob": search_blob,
            }
        )
        enriched.append(out)

    return enriched


def semantic_tokens(query: str) -> list[str]:
    base = [t for t in re.split(r"[^a-zA-Z0-9]+", query.lower()) if t]
    expanded = set(base)
    for token in base:
        expanded.update(SEMANTIC_HINTS.get(token, []))
    return list(expanded)


def infer_allergy_intent(query_text: str) -> str | None:
    """
    Infer allergy intent from free-text query.
    Returns:
    - "yes": looking for patients with allergies
    - "no": looking for patients without allergies
    - None: no strong intent
    """
    q = query_text.lower().strip()
    if not q:
        return None

    has_allergy_word = bool(re.search(r"\ballerg(y|ies|ic)\b", q))
    has_specific_allergen = bool(
        re.search(r"\b(peanut|penicillin|sulfa|anaphylaxis|hives|intolerance)\b", q)
    )

    if re.search(r"\b(no|without|none|free of)\b.*\ballerg", q):
        return "no"
    if re.search(r"\b(no known allergies?|nka)\b", q):
        return "no"

    if has_specific_allergen:
        return "yes"
    if has_allergy_word and re.search(r"\b(has|with|known|history of|patients? with)\b", q):
        return "yes"

    return None


def score_patient(patient: dict[str, Any], query: str) -> tuple[int, list[str]]:
    q = query.strip().lower()
    if not q:
        return 0, []

    tokens = semantic_tokens(q)
    sections = patient.get("sections", {})
    encounter_text = "\n".join(
        [
            e.get("title", "") + " " + e.get("reason_for_visit", "") + " " + e.get("full_text", "")
            for e in patient.get("encounters", [])
        ]
    ).lower()

    fields = {
        "name": patient.get("name", "").lower(),
        "profile": (
            f"{patient.get('address', '')} {patient.get('ethnicity', '')} "
            f"{patient.get('sex_gender', '')} {' '.join(patient.get('organizations', []))} "
            f"{' '.join(patient.get('practitioners', []))}"
        ).lower(),
        "conditions": "\n".join(sections.get("problem_list", [])).lower(),
        "allergies": "\n".join(sections.get("allergies", [])).lower(),
        "medications": "\n".join(sections.get("medications", [])).lower(),
        "encounters": encounter_text,
        "other": patient.get("search_blob", "").lower(),
    }

    score = 0
    matched: set[str] = set()

    if q in fields["other"]:
        score += 14

    for token in tokens:
        if token in fields["name"]:
            score += 14
            matched.add("name")
        if token in fields["conditions"]:
            score += 10
            matched.add("problem list")
        if token in fields["allergies"]:
            score += 9
            matched.add("allergies")
        if token in fields["medications"]:
            score += 8
            matched.add("medications")
        if token in fields["encounters"]:
            score += 7
            matched.add("encounters")
        if token in fields["profile"]:
            score += 5
            matched.add("profile")
        if token in fields["other"]:
            score += 1

    # Query mentions allergy and this patient actually has a known allergy.
    # Boost positive matches to avoid "No known allergies" dominating results.
    allergy_intent = infer_allergy_intent(q)
    if allergy_intent == "yes" and patient.get("known_allergy"):
        score += 12
    if allergy_intent == "yes" and not patient.get("known_allergy"):
        score -= 8
    if allergy_intent == "no" and not patient.get("known_allergy"):
        score += 8

    return score, sorted(matched)


def facet_counts(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        if not item:
            continue
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _passes_date_range(patient: dict[str, Any], date_from: str, date_to: str) -> bool:
    if not date_from and not date_to:
        return True

    patient_dates = [parse_iso_date(e.get("date", "")) for e in patient.get("encounters", [])]
    patient_dates = [d for d in patient_dates if d is not None]
    if not patient_dates:
        return False

    start = parse_iso_date(date_from) if date_from else None
    end = parse_iso_date(date_to) if date_to else None

    for d in patient_dates:
        if start and d < start:
            continue
        if end and d > end:
            continue
        return True

    return False


def filter_patients(patients: list[dict[str, Any]], query: dict[str, list[str]]) -> list[dict[str, Any]]:
    text = (query.get("q", [""])[0] or "").strip()
    city = (query.get("city", [""])[0] or "").strip()
    province = (query.get("province", [""])[0] or "").strip()
    sex_gender = (query.get("sex_gender", [""])[0] or "").strip()
    ethnicity = (query.get("ethnicity", [""])[0] or "").strip()
    allergy = (query.get("known_allergy", ["all"])[0] or "all").strip().lower()
    organization = (query.get("organization", [""])[0] or "").strip()
    practitioner = (query.get("practitioner", [""])[0] or "").strip()
    encounter_type = (query.get("encounter_type", [""])[0] or "").strip()
    setting = (query.get("setting", [""])[0] or "").strip()
    date_from = (query.get("date_from", [""])[0] or "").strip()
    date_to = (query.get("date_to", [""])[0] or "").strip()

    min_age_raw = (query.get("min_age", [""])[0] or "").strip()
    max_age_raw = (query.get("max_age", [""])[0] or "").strip()
    min_age = int(min_age_raw) if min_age_raw.isdigit() else None
    max_age = int(max_age_raw) if max_age_raw.isdigit() else None

    # If UI filter is not explicitly set, infer allergy intent from semantic query.
    if allergy == "all":
        inferred = infer_allergy_intent(text)
        if inferred in {"yes", "no"}:
            allergy = inferred

    filtered: list[dict[str, Any]] = []

    for patient in patients:
        p_city = patient.get("location", {}).get("city", "")
        p_province = patient.get("location", {}).get("province", "")

        if city and city != p_city:
            continue
        if province and province != p_province:
            continue
        if sex_gender and sex_gender != patient.get("sex_gender", ""):
            continue
        if ethnicity and ethnicity != patient.get("ethnicity", ""):
            continue
        if allergy == "yes" and not patient.get("known_allergy"):
            continue
        if allergy == "no" and patient.get("known_allergy"):
            continue
        if organization and organization not in patient.get("organizations", []):
            continue
        if practitioner and practitioner not in patient.get("practitioners", []):
            continue
        if encounter_type and encounter_type not in patient.get("encounter_types", []):
            continue
        if setting and setting not in patient.get("encounter_settings", []):
            continue
        if min_age is not None and (patient.get("age") is None or patient.get("age") < min_age):
            continue
        if max_age is not None and (patient.get("age") is None or patient.get("age") > max_age):
            continue
        if not _passes_date_range(patient, date_from, date_to):
            continue

        score, matched = score_patient(patient, text)
        if text and score == 0:
            continue

        p2 = dict(patient)
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
        total_encounters = sum(int(p.get("encounter_count", 0)) for p in self.patients)

        city_counts = facet_counts([p.get("location", {}).get("city", "") for p in self.patients])
        province_counts = facet_counts([p.get("location", {}).get("province", "") for p in self.patients])
        sex_gender_counts = facet_counts([p.get("sex_gender", "") for p in self.patients])
        ethnicity_counts = facet_counts([p.get("ethnicity", "") for p in self.patients])
        organization_counts = facet_counts([org for p in self.patients for org in p.get("organizations", [])])
        practitioner_counts = facet_counts([pr for p in self.patients for pr in p.get("practitioners", [])])
        encounter_type_counts = facet_counts([t for p in self.patients for t in p.get("encounter_types", [])])
        setting_counts = facet_counts([s for p in self.patients for s in p.get("encounter_settings", [])])

        return {
            "total_patients": len(self.patients),
            "total_encounters": total_encounters,
            "known_allergy_count": known_allergy_count,
            "city_counts": city_counts,
            "province_counts": province_counts,
            "sex_gender_counts": sex_gender_counts,
            "ethnicity_counts": ethnicity_counts,
            "organization_counts": organization_counts,
            "practitioner_counts": practitioner_counts,
            "encounter_type_counts": encounter_type_counts,
            "setting_counts": setting_counts,
        }


class Handler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        directory: str | None = None,
        state: AppState | None = None,
        **kwargs: Any,
    ) -> None:
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
            self._send_json({"count": len(results), "results": results})
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
    encounters_by_patient = load_encounters()
    organizations = parse_roster_file(ORGANIZATION_FILE)
    practitioners = parse_roster_file(PRACTITIONER_FILE)

    enriched_patients = enrich_patients(
        patients=patients,
        encounters_by_patient=encounters_by_patient,
        organizations=organizations,
        practitioners=practitioners,
    )

    state = AppState(patients=enriched_patients)
    server = ThreadingHTTPServer((args.host, args.port), build_handler(state))

    print(f"Patient explorer running at http://{args.host}:{args.port}")
    print(f"Loaded {len(enriched_patients)} patient records from {PATIENT_DIR}")
    print(f"Loaded {sum(len(p.get('encounters', [])) for p in enriched_patients)} encounters from {ENCOUNTER_DIR}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

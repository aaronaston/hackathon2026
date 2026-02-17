# Clinical Document Indexing Sandbox

This repository is a working sandbox for experiments in clinical document indexing, query, and retrieval.

## Current Direction
The project focus is building and validating workflows for:
- Parsing healthcare documents into structured fields
- Indexing extracted content for search and retrieval
- Testing query behavior across realistic clinical-style records

Everything created so far is setup/background data for that core effort.

## Current Data Assets
- `reference/forms`
  - Source clinical forms (for example Ontario lab requisition PDFs)
- `test-data/patients`
  - 30 synthetic IPS-style patient summaries in markdown
- `scripts/fill_lab_req_sample.py`
  - Utility used to populate an Ontario lab requisition PDF sample
- `scripts/generate_patients.py`
  - Generator for the synthetic patient markdown cohort
- `generating-test-patients.md`
  - Method notes and source references for patient data generation

## Working with the Patient Dataset
Regenerate the patient summaries:

```bash
python3 scripts/generate_patients.py
```

This writes files to `test-data/patients`.

## Filling a Sample Ontario Lab Requisition
Use `scripts/fill_lab_req_sample.py` to populate a sample copy of the Ontario lab requisition form.

Prerequisites:
- Python 3.11+
- `pypdf` and `cryptography`

Install dependencies:

```bash
python3 -m pip install --user pypdf cryptography
```

Run from repo root:

```bash
python3 scripts/fill_lab_req_sample.py
```

Input/output:
- Input PDF: `OntarioLabReq-4422-84.pdf` (repo root)
- Output PDF: `OntarioLabReq-4422-84-sample-filled.pdf` (repo root)

Customize the sample:
- Edit the `field_values` dictionary in `scripts/fill_lab_req_sample.py`.
- Text fields accept strings.
- Checkbox/radio fields require their PDF state values (for example `/Yes`, `/M`, `/ohip`, `/fasting`).
- Keep duplicate demographic fields aligned (`patienFname`/`fname`, `patienLname`/`lname`, DOB fields) so both parts of the form are consistent.
- Keep `Health Number` to the form field max length (10 characters in this form).

## Near-Term Next Steps
1. Define a canonical document schema for parsed output (patient, encounter, orders, observations, provenance).
2. Build parsers/extractors for each document type in `reference/forms`.
3. Stand up an index layer and retrieval API (keyword + structured filters).
4. Create evaluation queries and expected-answer fixtures to measure retrieval quality.
5. Add regression tests so extraction/index changes are measurable and safe.

## Data Safety
- Treat all content here as test/synthetic unless explicitly marked otherwise.
- Do not add real PHI/PII without explicit governance and controls.

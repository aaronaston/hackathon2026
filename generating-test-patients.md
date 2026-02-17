# Generating Test Patients

This document records how the synthetic patient set in `test-data/patients` was generated.

## Goal
Create a small, realistic-looking synthetic cohort for experiments in clinical document parsing, indexing, retrieval, and query evaluation.

## Output
- 30 markdown files in `test-data/patients`
- Naming format: `DD-FirstnameLastname.md` (for example `01-LucasMcLeod.md`)
- One short IPS-style summary per patient

## Script
- Generator: `scripts/generate_patients.py`
- Run with:

```bash
python3 scripts/generate_patients.py
```

## Generation Approach
1. Defined a fixed cohort of 30 fictional patients directly in the script.
2. Modeled broad population characteristics after southern Ontario patterns:
- Mixed age distribution (children to older adults)
- Near-balanced sex/gender representation
- Diverse ethnicity mix reflecting Ontario urban demographics
- Addresses distributed across GTA and other southern Ontario municipalities
3. Used IPS-inspired section structure for each record:
- `Problem List (Required)`
- `Allergies and Intolerances (Required)`
- `Medication Summary (Required)`
- plus immunizations, diagnostic results, procedures, social history, vitals, and plan of care
4. Computed age from DOB as of `2026-02-16` and wrote that into each file.

## Reference Sources Used
- HL7 FHIR IPS structure:
  - https://hl7.org/fhir/uv/ips/STU2/Structure-of-the-International-Patient-Summary.html
- Statistics Canada 2021 Census profile for Ontario (age and population context):
  - https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/page.cfm?DGUIDlist=2021A000235&GENDERlist=1&HEADERlist=0&Lang=E&STATISTIClist=1&SearchText=ontario
- Statistics Canada 2021 Census visible minority/ethnicity context (Ontario urban comparison source used during drafting):
  - https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/removegeo.cfm?DGUID=2021A00053521005&DGUIDlist=2021A00053521005%2C2021A000235&GENDERlist=1%2C2%2C3&HEADERlist=31%2C32%2C30&Lang=E&STATISTIClist=1&SearchText=Mississauga

## Notes and Constraints
- These records are synthetic and intended only for test data workflows.
- They are not statistically weighted or representative for clinical inference.
- The intent is realism for document-processing experiments, not epidemiologic accuracy.

from datetime import date
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
out_dir = repo_root / 'test-data' / 'patients'
out_dir.mkdir(parents=True, exist_ok=True)

today = date(2026, 2, 16)

patients = [
    {
        'first':'Lucas','last':'McLeod','gender':'Male','dob':'2020-09-04','ethnicity':'White (Scottish/Irish Canadian)','address':'18 Parkside Dr, Guelph, ON N1E 0A9',
        'problems':'Mild intermittent asthma.',
        'allergies':'Peanut allergy (hives); carries epinephrine auto-injector.',
        'meds':'Salbutamol inhaler PRN.',
        'immunizations':'Routine childhood vaccines up to date; annual influenza vaccine.',
        'results':'No recent abnormal labs; oxygen saturation normal at last visit.',
        'procedures':'None.',
        'social':'Lives with parents; no smoke exposure at home.',
        'vitals':'Height 110 cm; weight 19.8 kg; BP not routinely measured.',
        'plan':'Continue asthma action plan and annual follow-up.'
    },
    {
        'first':'Maya','last':'Chen','gender':'Female','dob':'2016-03-11','ethnicity':'Chinese','address':'241 Birchview Cres, Markham, ON L3R 8V3',
        'problems':'Atopic dermatitis (mild).',
        'allergies':'No known drug allergies.',
        'meds':'Hydrocortisone 1% cream PRN flares.',
        'immunizations':'Age-appropriate immunizations complete.',
        'results':'Normal CBC and ferritin in 2025.',
        'procedures':'None.',
        'social':'Student; active in swimming twice weekly.',
        'vitals':'Height 137 cm; weight 32.0 kg.',
        'plan':'Skin care regimen; reassess if flare frequency increases.'
    },
    {
        'first':'Noah','last':'Patel','gender':'Male','dob':'2012-07-22','ethnicity':'South Asian (Indian)','address':'77 Sandalwood Pkwy E, Brampton, ON L6Z 1Y5',
        'problems':'No chronic medical problems.',
        'allergies':'No known allergies.',
        'meds':'No current medications.',
        'immunizations':'Childhood series complete; HPV series started.',
        'results':'Normal lipid screen due to family history review.',
        'procedures':'None.',
        'social':'Plays soccer; no tobacco/alcohol exposure.',
        'vitals':'Height 156 cm; weight 48.6 kg; BMI 20.0.',
        'plan':'Routine preventive care and completion of HPV series.'
    },
    {
        'first':'Ava','last':'Singh','gender':'Female','dob':'2008-11-30','ethnicity':'South Asian (Punjabi)','address':'3903 Elmwood Ave, Windsor, ON N8Y 3H8',
        'problems':'Iron deficiency without anemia (improving).',
        'allergies':'No known drug allergies.',
        'meds':'Ferrous sulfate 300 mg PO daily.',
        'immunizations':'Routine vaccines up to date; influenza vaccine 2025.',
        'results':'Ferritin improved from 11 to 24 ug/L over 6 months.',
        'procedures':'None.',
        'social':'High school student; vegetarian diet.',
        'vitals':'Height 163 cm; weight 56.1 kg; BP 108/66.',
        'plan':'Continue iron for 3 more months and recheck ferritin.'
    },
    {
        'first':'Ethan','last':'Brown','gender':'Male','dob':'2004-05-19','ethnicity':'Black (Caribbean)','address':'90 Lakeshore Rd E, Oakville, ON L6J 1H8',
        'problems':'Seasonal allergic rhinitis.',
        'allergies':'No known drug allergies.',
        'meds':'Cetirizine 10 mg PO daily PRN in spring.',
        'immunizations':'Routine schedule complete; COVID-19 boosters up to 2024.',
        'results':'Normal CBC and TSH (2025).',
        'procedures':'None.',
        'social':'University student; occasional alcohol, no tobacco.',
        'vitals':'Height 182 cm; weight 77.4 kg; BP 116/72.',
        'plan':'Continue PRN antihistamine and annual wellness check.'
    },
    {
        'first':'Sofia','last':'Rossi','gender':'Female','dob':'2001-01-14','ethnicity':'White (Italian Canadian)','address':'14 Queen St N, Kitchener, ON N2H 2G8',
        'problems':'Migraine without aura (episodic).',
        'allergies':'Penicillin allergy (rash).',
        'meds':'Rizatriptan 10 mg PO PRN migraine; naproxen PRN.',
        'immunizations':'Routine immunizations complete.',
        'results':'No neurologic red flags; normal CBC/chemistry.',
        'procedures':'None.',
        'social':'Works in retail; sleep variability during shift work.',
        'vitals':'Height 168 cm; weight 63.0 kg; BP 110/70.',
        'plan':'Trigger management, headache diary, reassess in 6 months.'
    },
    {
        'first':'Daniel','last':'Nguyen','gender':'Male','dob':'1997-08-03','ethnicity':'Southeast Asian (Vietnamese)','address':'455 Dundas St W, Mississauga, ON L5B 1J5',
        'problems':'No chronic conditions.',
        'allergies':'No known allergies.',
        'meds':'No current medications.',
        'immunizations':'Tetanus booster 2023; influenza 2025.',
        'results':'Baseline metabolic panel and lipids normal (2025).',
        'procedures':'Wisdom tooth extraction (2018).',
        'social':'Software engineer; sedentary work, exercises 3 times/week.',
        'vitals':'Height 175 cm; weight 73.5 kg; BP 118/74.',
        'plan':'Continue preventive screening and lifestyle counseling.'
    },
    {
        'first':'Isabella','last':'Khan','gender':'Female','dob':'1995-10-09','ethnicity':'Mixed (Pakistani and White Canadian)','address':'120 Hurontario St, Collingwood, ON L9Y 2L8',
        'problems':'Generalized anxiety disorder (stable).',
        'allergies':'No known drug allergies.',
        'meds':'Sertraline 50 mg PO daily.',
        'immunizations':'Routine immunizations current; influenza 2025.',
        'results':'TSH normal; PHQ-9 and GAD-7 improved over past year.',
        'procedures':'None.',
        'social':'Lives with partner; no tobacco; occasional alcohol.',
        'vitals':'Height 165 cm; weight 61.2 kg; BP 112/68.',
        'plan':'Continue SSRI and periodic mental health follow-up.'
    },
    {
        'first':'Owen','last':'Tremblay','gender':'Male','dob':'1993-04-26','ethnicity':'White (French Canadian)','address':'62 Albert St, London, ON N6A 1L1',
        'problems':'Gastroesophageal reflux disease.',
        'allergies':'No known allergies.',
        'meds':'Pantoprazole 40 mg PO daily.',
        'immunizations':'Routine vaccines up to date.',
        'results':'H. pylori stool antigen negative (2024).',
        'procedures':'Upper endoscopy (2024), mild esophagitis.',
        'social':'Chef; late meals and caffeine contribute to symptoms.',
        'vitals':'Height 178 cm; weight 82.1 kg; BP 122/78.',
        'plan':'Continue PPI; diet modification; step-down trial when stable.'
    },
    {
        'first':'Chloe','last':'Wilson','gender':'Female','dob':'1991-12-18','ethnicity':'White (English Canadian)','address':'312 Main St W, Hamilton, ON L8P 1J9',
        'problems':'Hypothyroidism (primary).',
        'allergies':'No known drug allergies.',
        'meds':'Levothyroxine 100 mcg PO daily.',
        'immunizations':'Influenza 2025; COVID-19 booster 2024.',
        'results':'TSH 2.3 mIU/L (controlled).',
        'procedures':'None.',
        'social':'Teacher; nonsmoker; moderate exercise.',
        'vitals':'Height 170 cm; weight 69.4 kg; BP 114/72.',
        'plan':'Continue current dose; annual TSH monitoring.'
    },
    {
        'first':'Marcus','last':'Ali','gender':'Male','dob':'1989-06-01','ethnicity':'Arab (Lebanese)','address':'88 King St E, Oshawa, ON L1H 1B6',
        'problems':'Dyslipidemia (mild).',
        'allergies':'No known allergies.',
        'meds':'Rosuvastatin 10 mg PO nightly.',
        'immunizations':'Routine adult immunizations current.',
        'results':'LDL-C improved from 4.1 to 2.2 mmol/L.',
        'procedures':'None.',
        'social':'Accountant; former smoker (quit 2019).',
        'vitals':'Height 180 cm; weight 86.0 kg; BP 126/80.',
        'plan':'Continue statin and annual lipid panel.'
    },
    {
        'first':'Amelia','last':'Baptiste','gender':'Female','dob':'1987-02-27','ethnicity':'Black (African Canadian)','address':'47 Talbot St, St. Thomas, ON N5P 1A3',
        'problems':'Type 2 diabetes mellitus.',
        'allergies':'No known drug allergies.',
        'meds':'Metformin 1000 mg PO BID.',
        'immunizations':'Influenza 2025; pneumococcal vaccine documented.',
        'results':'A1c 7.1% (2025), urine ACR normal.',
        'procedures':'Retinal screening completed 2025 (no retinopathy).',
        'social':'Personal support worker; no tobacco; walks daily.',
        'vitals':'Height 167 cm; weight 78.3 kg; BP 124/76.',
        'plan':'Continue metformin; repeat A1c and renal screening in 3-6 months.'
    },
    {
        'first':'Harpreet','last':'Dhillon','gender':'Male','dob':'1985-09-15','ethnicity':'South Asian (Punjabi Sikh)','address':'5000 Yonge St, Toronto, ON M2N 7E9',
        'problems':'Hypertension.',
        'allergies':'No known allergies.',
        'meds':'Perindopril 8 mg PO daily.',
        'immunizations':'Influenza 2025; tetanus booster 2022.',
        'results':'Creatinine and potassium stable; BP controlled.',
        'procedures':'None.',
        'social':'Truck driver; reduced sodium diet in progress.',
        'vitals':'Height 176 cm; weight 84.7 kg; BP 128/78.',
        'plan':'Continue ACE inhibitor and home BP log.'
    },
    {
        'first':'Natalie','last':'Morrison','gender':'Female','dob':'1984-04-12','ethnicity':'White (Irish Canadian)','address':'112 Brock St, Kingston, ON K7L 1R4',
        'problems':'Major depressive disorder in remission.',
        'allergies':'No known drug allergies.',
        'meds':'Escitalopram 10 mg PO daily.',
        'immunizations':'Routine vaccines up to date.',
        'results':'Stable mood scales over last 12 months.',
        'procedures':'None.',
        'social':'Librarian; rare alcohol use; nonsmoker.',
        'vitals':'Height 164 cm; weight 64.5 kg; BP 112/70.',
        'plan':'Maintain therapy and medication; routine follow-up.'
    },
    {
        'first':'Andre','last':'Lefebvre','gender':'Male','dob':'1982-01-06','ethnicity':'White (French/Metis)','address':'29 Maple Ave, Barrie, ON L4N 1R7',
        'problems':'Obstructive sleep apnea.',
        'allergies':'No known allergies.',
        'meds':'No regular prescriptions.',
        'immunizations':'Influenza 2025 documented.',
        'results':'Sleep study AHI consistent with moderate OSA.',
        'procedures':'CPAP initiation (2023).',
        'social':'Construction supervisor; former smoker.',
        'vitals':'Height 183 cm; weight 96.2 kg; BP 130/82.',
        'plan':'Continue nightly CPAP and weight-management counseling.'
    },
    {
        'first':'Priya','last':'Iyer','gender':'Female','dob':'1980-08-21','ethnicity':'South Asian (Tamil)','address':'66 Brock St S, Whitby, ON L1N 4J5',
        'problems':'Prediabetes.',
        'allergies':'No known drug allergies.',
        'meds':'No antihyperglycemic medications.',
        'immunizations':'Influenza 2025; COVID-19 booster 2024.',
        'results':'A1c 6.0%; fasting glucose mildly elevated.',
        'procedures':'None.',
        'social':'Office manager; increasing physical activity.',
        'vitals':'Height 161 cm; weight 70.6 kg; BP 118/74.',
        'plan':'Lifestyle treatment and repeat A1c in 6 months.'
    },
    {
        'first':'Ryan','last':'Kowalski','gender':'Male','dob':'1978-05-03','ethnicity':'White (Polish Canadian)','address':'202 Dalhousie St, Brantford, ON N3T 2J5',
        'problems':'Chronic low back pain.',
        'allergies':'No known allergies.',
        'meds':'Naproxen 250 mg PO PRN; physiotherapy exercises.',
        'immunizations':'Routine immunizations documented.',
        'results':'No neurologic deficits; imaging not recently required.',
        'procedures':'Lumbar steroid injection (2022).',
        'social':'Warehouse work; no tobacco, occasional alcohol.',
        'vitals':'Height 179 cm; weight 88.9 kg; BP 124/80.',
        'plan':'Continue conservative management and core-strength program.'
    },
    {
        'first':'Gabriela','last':'Silva','gender':'Female','dob':'1976-10-28','ethnicity':'Latin American (Brazilian)','address':'41 Ottawa St N, Kitchener, ON N2H 3K9',
        'problems':'Hypertension and dyslipidemia.',
        'allergies':'No known drug allergies.',
        'meds':'Amlodipine 5 mg PO daily; atorvastatin 20 mg PO nightly.',
        'immunizations':'Influenza 2025; shingles vaccine dose 1 complete.',
        'results':'BP and LDL improved on therapy.',
        'procedures':'None.',
        'social':'Restaurant owner; reduced sodium intake underway.',
        'vitals':'Height 160 cm; weight 72.2 kg; BP 126/78.',
        'plan':'Continue treatment; complete shingles series.'
    },
    {
        'first':'David','last':'Oconnor','gender':'Male','dob':'1974-03-17','ethnicity':'White (Irish Canadian)','address':'85 George St, Peterborough, ON K9J 3G3',
        'problems':'Atrial fibrillation (paroxysmal).',
        'allergies':'No known allergies.',
        'meds':'Apixaban 5 mg PO BID; metoprolol succinate 25 mg PO daily.',
        'immunizations':'Routine adult vaccines up to date.',
        'results':'Renal function stable; no recent AF-related admissions.',
        'procedures':'Electrical cardioversion (2021).',
        'social':'Retired paramedic; no tobacco.',
        'vitals':'Height 177 cm; weight 82.7 kg; BP 122/76; pulse irregularly irregular.',
        'plan':'Continue anticoagulation and cardiology follow-up.'
    },
    {
        'first':'Melissa','last':'Tran','gender':'Female','dob':'1972-12-05','ethnicity':'Chinese-Vietnamese','address':'140 Erie St, Stratford, ON N5A 2M4',
        'problems':'Primary osteoarthritis (knees).',
        'allergies':'No known drug allergies.',
        'meds':'Acetaminophen PRN; topical diclofenac PRN.',
        'immunizations':'Influenza 2025; COVID-19 booster 2024.',
        'results':'Knee x-ray with mild-moderate degenerative change.',
        'procedures':'Intra-articular corticosteroid injection (2024).',
        'social':'Administrative assistant; walks daily with pacing.',
        'vitals':'Height 158 cm; weight 66.8 kg; BP 120/74.',
        'plan':'Exercise therapy and analgesia optimization.'
    },
    {
        'first':'Aaron','last':'Aston','gender':'Male','dob':'1972-06-14','ethnicity':'White (English Canadian)','address':'102-543 Timothy St, Newmarket, ON L3Y 0M0',
        'problems':'No active chronic diagnoses documented.',
        'allergies':'No known drug allergies.',
        'meds':'No regular medications.',
        'immunizations':'Influenza 2025 documented; routine adult vaccines current.',
        'results':'Annual baseline bloodwork ordered (CBC, fasting glucose, A1c, renal, liver, lipids, TSH).',
        'procedures':'None significant reported.',
        'social':'Works in technology; nonsmoker; occasional alcohol.',
        'vitals':'Height 181 cm; weight 84.0 kg; BP 124/78.',
        'plan':'Review pending lab results and maintain annual preventive care.'
    },
    {
        'first':'Leanne','last':'George','gender':'Female','dob':'1970-01-31','ethnicity':'Indigenous (Anishinaabe)','address':'73 Market St, Sault Ste. Marie, ON P6A 2Y2',
        'problems':'Type 2 diabetes mellitus and hypertension.',
        'allergies':'No known allergies.',
        'meds':'Metformin 500 mg PO BID; ramipril 10 mg PO daily.',
        'immunizations':'Influenza 2025; pneumococcal vaccine documented.',
        'results':'A1c 7.4%; urine ACR mildly elevated.',
        'procedures':'Retinal exam 2025 (mild non-proliferative changes).',
        'social':'Community health worker; quit smoking 2020.',
        'vitals':'Height 162 cm; weight 80.1 kg; BP 132/80.',
        'plan':'Tighten glycemic control and continue renal protection strategies.'
    },
    {
        'first':'Farah','last':'Rahimi','gender':'Female','dob':'1968-09-07','ethnicity':'West Asian (Iranian)','address':'18 Brock St, Niagara Falls, ON L2E 3R3',
        'problems':'Hypothyroidism and osteoporosis.',
        'allergies':'No known drug allergies.',
        'meds':'Levothyroxine 88 mcg PO daily; alendronate 70 mg weekly; vitamin D.',
        'immunizations':'Influenza 2025; shingles series complete.',
        'results':'TSH in target range; DEXA shows low bone density (stable).',
        'procedures':'None.',
        'social':'Lives with spouse; no tobacco/alcohol.',
        'vitals':'Height 157 cm; weight 59.7 kg; BP 118/72.',
        'plan':'Continue bone health regimen and annual fall-risk review.'
    },
    {
        'first':'Jason','last':'Walker','gender':'Male','dob':'1966-04-24','ethnicity':'White (Scottish Canadian)','address':'92 Main St, Cambridge, ON N1R 1V6',
        'problems':'Coronary artery disease, post PCI.',
        'allergies':'No known allergies.',
        'meds':'ASA 81 mg daily; rosuvastatin 20 mg nightly; bisoprolol 5 mg daily.',
        'immunizations':'Influenza 2025; pneumococcal vaccine complete.',
        'results':'LDL at secondary prevention target; no angina symptoms.',
        'procedures':'PCI with stent (2019).',
        'social':'Retired machinist; former smoker.',
        'vitals':'Height 174 cm; weight 79.3 kg; BP 120/72.',
        'plan':'Continue secondary prevention and annual cardiology follow-up.'
    },
    {
        'first':'Cynthia','last':'Mensah','gender':'Female','dob':'1963-11-02','ethnicity':'Black (Ghanaian Canadian)','address':'155 Front St, Belleville, ON K8N 2Y6',
        'problems':'Chronic kidney disease stage 3a.',
        'allergies':'No known drug allergies.',
        'meds':'Losartan 50 mg PO daily; vitamin D3.',
        'immunizations':'Influenza 2025; COVID-19 booster 2024.',
        'results':'eGFR stable around 52 mL/min/1.73m2; potassium normal.',
        'procedures':'Renal ultrasound (2023) without obstruction.',
        'social':'Part-time caregiver; no tobacco.',
        'vitals':'Height 166 cm; weight 74.0 kg; BP 126/76.',
        'plan':'Monitor renal function and BP every 6 months.'
    },
    {
        'first':'Mohammed','last':'Haddad','gender':'Male','dob':'1960-06-09','ethnicity':'Arab (Syrian)','address':'33 Durham St, Sudbury, ON P3C 3M5',
        'problems':'COPD (moderate).',
        'allergies':'No known allergies.',
        'meds':'Tiotropium inhaler daily; salbutamol inhaler PRN.',
        'immunizations':'Influenza 2025; pneumococcal vaccines documented.',
        'results':'Spirometry consistent with moderate airflow limitation.',
        'procedures':'None.',
        'social':'Former smoker (40 pack-years, quit 2018).',
        'vitals':'Height 171 cm; weight 76.8 kg; BP 128/78; SpO2 95% RA.',
        'plan':'Maintain inhaler adherence and pulmonary rehab exercises.'
    },
    {
        'first':'Patricia','last':'DiMarco','gender':'Female','dob':'1957-08-16','ethnicity':'White (Italian Canadian)','address':'60 Geneva St, St. Catharines, ON L2R 4M7',
        'problems':'Osteopenia and GERD.',
        'allergies':'Sulfa allergy (rash).',
        'meds':'Pantoprazole 20 mg daily; calcium/vitamin D.',
        'immunizations':'Influenza 2025; shingles series complete.',
        'results':'DEXA with osteopenia, no fracture history.',
        'procedures':'Colonoscopy 2022 (normal).',
        'social':'Retired; active in community walking group.',
        'vitals':'Height 159 cm; weight 63.9 kg; BP 118/70.',
        'plan':'Bone health monitoring and reflux step-down as tolerated.'
    },
    {
        'first':'Stephen','last':'Lee','gender':'Male','dob':'1953-02-23','ethnicity':'Chinese','address':'12 King St S, Waterloo, ON N2J 1N8',
        'problems':'Type 2 diabetes mellitus and hyperlipidemia.',
        'allergies':'No known allergies.',
        'meds':'Metformin 1000 mg BID; empagliflozin 10 mg daily; atorvastatin 40 mg nightly.',
        'immunizations':'Influenza 2025; pneumococcal and shingles complete.',
        'results':'A1c 7.0%; LDL at target; kidney function stable.',
        'procedures':'Cataract surgery (left eye, 2023).',
        'social':'Retired engineer; no tobacco; occasional wine.',
        'vitals':'Height 169 cm; weight 71.5 kg; BP 124/74.',
        'plan':'Continue current regimen and annual retinal/foot screening.'
    },
    {
        'first':'Margaret','last':'Collins','gender':'Female','dob':'1948-05-29','ethnicity':'White (English Canadian)','address':'9 Division St, Cobourg, ON K9A 3R1',
        'problems':'Atrial fibrillation and osteoarthritis.',
        'allergies':'No known drug allergies.',
        'meds':'Warfarin per INR clinic; diltiazem ER 120 mg daily.',
        'immunizations':'Influenza 2025; pneumococcal complete.',
        'results':'INR generally therapeutic; renal function stable.',
        'procedures':'Right total knee arthroplasty (2020).',
        'social':'Widowed; independent in ADLs.',
        'vitals':'Height 163 cm; weight 68.7 kg; BP 122/70.',
        'plan':'Continue anticoagulation monitoring and fall prevention.'
    },
    {
        'first':'Eleanor','last':'Davis','gender':'Female','dob':'1939-01-20','ethnicity':'White (English Canadian)','address':'44 Welland Ave, Welland, ON L3B 3B6',
        'problems':'Mild cognitive impairment; hypertension.',
        'allergies':'No known drug allergies.',
        'meds':'Amlodipine 5 mg daily; donepezil 5 mg nightly.',
        'immunizations':'Influenza 2025 and COVID-19 booster 2024 recorded.',
        'results':'B12 and TSH normal during cognitive workup.',
        'procedures':'None.',
        'social':'Lives with daughter; needs support for medications.',
        'vitals':'Height 155 cm; weight 57.4 kg; BP 130/74.',
        'plan':'Medication supervision and periodic cognitive reassessment.'
    }
]

assert len(patients) == 30

def age_from_dob(dob: str) -> int:
    y, m, d = map(int, dob.split('-'))
    years = today.year - y - ((today.month, today.day) < (m, d))
    return years

for i, p in enumerate(patients, 1):
    dd = f"{i:02d}"
    fname = f"{dd}-{p['first']}{p['last']}.md"
    path = out_dir / fname
    age = age_from_dob(p['dob'])
    text = f"""# IPS Patient Summary

## Patient
- Name: {p['first']} {p['last']}
- Sex/Gender: {p['gender']}
- Date of birth: {p['dob']} (Age {age} as of 2026-02-16)
- Ethnicity: {p['ethnicity']}
- Address: {p['address']}
- Summary date: 2026-02-16

## Problem List (Required)
- {p['problems']}

## Allergies and Intolerances (Required)
- {p['allergies']}

## Medication Summary (Required)
- {p['meds']}

## Immunizations
- {p['immunizations']}

## Diagnostic Results
- {p['results']}

## History of Procedures
- {p['procedures']}

## Social History
- {p['social']}

## Vital Signs
- {p['vitals']}

## Plan of Care
- {p['plan']}
"""
    path.write_text(text)

print(f"Wrote {len(patients)} files to {out_dir}")

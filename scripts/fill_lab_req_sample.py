from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

input_pdf = 'OntarioLabReq-4422-84.pdf'
output_pdf = 'OntarioLabReq-4422-84-sample-filled.pdf'

reader = PdfReader(input_pdf)
if reader.is_encrypted:
    reader.decrypt('')

writer = PdfWriter()
writer.clone_document_from_reader(reader)

if '/AcroForm' in writer._root_object:
    writer._root_object['/AcroForm'][NameObject('/NeedAppearances')] = BooleanObject(True)

field_values = {
    # Practitioner information
    'Date': '2026-02-16',
    'name': 'Dr. Priya Menon, MD CCFP',
    'address': 'Newmarket Family Health Centre\\n210 Eagle St W, Newmarket, ON L3Y 1J8',
    'contactNumber1': '905-555-0184',
    'ClinicianPractitioner Number': 'ON-PRAC-77421',
    'CPSO  Registration No': '112233',
    'clinicianTel': '905-555-0184',

    # Billing / coverage
    'checkOne': '/ohip',
    'clinician': '/ohip',

    # Patient demographics
    'Patient’s Last Name as per OHIP Card': 'Aston',
    'patienFname': 'Aaron',
    'patienLname': 'Aston',
    'Patient’s Address including Postal Code': '102-543 Timothy St, Newmarket, ON L3Y 0M0',
    'Health Number': '1234567890',
    'Province': 'ON',
    'patientTelephone': '905-555-0142',
    'sex': '/M',
    'y_birth2': '1972',
    'm_birth2': '06',
    'd_birth2': '14',

    # Duplicate patient fields present in the form layout
    'lname': 'Aston',
    'fname': 'Aaron',
    'address2a': '102-543 Timothy St, Newmarket, ON L3Y 0M0',
    'y_birth': '1972',
    'm_birth': '06',
    'd_birth': '14',

    # Clinical context
    'Additional Clinical Information eg diagnosis': 'Annual physical baseline bloodwork (asymptomatic).',

    # Baseline annual labs
    'hermatology1.0': '/fasting',  # CBC
    'row1.0': '/Yes',              # Glucose
    'biochemistry': '/fasting',    # Fasting indicator
    'row1.1': '/Yes',              # HbA1C
    'row1.2': '/Yes',              # Creatinine (eGFR)
    'row1.4': '/Yes',              # Sodium
    'row1.5': '/Yes',              # Potassium
    'row1.6': '/Yes',              # ALT
    'row1.7': '/Yes',              # Alk. Phosphatase
    'row1.8': '/Yes',              # Bilirubin
    'row1.9': '/Yes',              # Albumin
    'row1.13': '/Yes',             # Lipid assessment

    # Additional baseline blood test not explicitly listed in nearby checkboxes
    'Other Tests – one test per line, Row 15': 'TSH',
}

for page in writer.pages:
    writer.update_page_form_field_values(page, field_values, auto_regenerate=False)

with open(output_pdf, 'wb') as f:
    writer.write(f)

print(f'Wrote {output_pdf}')

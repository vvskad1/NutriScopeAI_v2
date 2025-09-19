import os
import pytest
from app.ingest import parser

# Path to a sample PDF for regression testing (update as needed)
SAMPLE_PDF = os.path.join(os.path.dirname(__file__), '../test_reports/lipid.pdf')

# Expected results for key tests (update as needed)
EXPECTED = {
    'S.HDL': {'value': 47.0, 'unit': 'mg/dL', 'bands': [
        {'label': 'Desirable', 'min': 60.0, 'unit': 'mg/dL', 'op': '>'}
    ]},
    'S.Total Cholesterol': {'value': 145.0, 'unit': 'mg/dL', 'high': 200.0},
    'S.Triglycerides': {'value': 63.0, 'unit': 'mg/dL'},
}

def test_lipid_profile_extraction():
    with open(SAMPLE_PDF, 'rb') as f:
        pdf_bytes = f.read()
    rows, conf = parser.parse_pdf_bytes(pdf_bytes)
    found = {r['test']: r for r in rows}
    for test, exp in EXPECTED.items():
        assert test in found, f"Missing test: {test}"
        for k, v in exp.items():
            assert found[test].get(k) == v, f"Mismatch for {test} field {k}: got {found[test].get(k)}, expected {v}"

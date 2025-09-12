# backend/app/ingest/aliases.py

import re

# Canonical keys (lower-case) we want to use across the app/KB
# Keep these stable: they’re what routes.py and KB expect.
CANONICAL = {
    # CBC counts
    "white blood cell (wbc)",
    "red blood cell (rbc)",
    "hemoglobin",
    "hematocrit",
    "mcv",
    "mch",
    "mchc",
    "rdw",
    "platelet count",
    "mpv",

    # 5-part differential (percent)
    "neutrophils %",
    "lymphocytes %",
    "monocytes %",
    "eosinophils %",
    "basophils %",

    # absolute counts
    "absolute neutrophils",
    "absolute lymphocytes",
    "absolute monocytes",
    "absolute eosinophils",
    "absolute basophils",

    # keep anything you already had, e.g. vitamins/lipids/chemistry…
    "vitamin d (25-oh)",
    "uric acid",
    # ...
}

# Rich alias map -> canonical key (all keys lower-cased)
ALIASES = {
    "haemoglobin": "hemoglobin",
    # CBC
    "white blood cell": "white blood cell (wbc)",
    "white blood cell (wbc)": "white blood cell (wbc)",
    "wbc": "white blood cell (wbc)",

    "red blood cell": "red blood cell (rbc)",
    "red blood cell (rbc)": "red blood cell (rbc)",
    "rbc": "red blood cell (rbc)",

    "hemoglobin": "hemoglobin",
    "hb": "hemoglobin",
    "hb/hgb": "hemoglobin",
    "hgb": "hemoglobin",

    "hematocrit": "hematocrit",
    "hct": "hematocrit",

    "mean cell volume": "mcv",
    "mean corpuscular volume": "mcv",
    "mcv": "mcv",

    "mean cell hemoglobin": "mch",
    "mean corpuscular hemoglobin": "mch",
    "mch": "mch",

    "mean cell hb conc": "mchc",
    "mean corpuscular hemoglobin concentration": "mchc",
    "mchc": "mchc",

    "red cell dist width": "rdw",
    "red cell distribution width": "rdw",
    "rdw": "rdw",

    "platelet count": "platelet count",
    "platelets": "platelet count",
    "plt": "platelet count",

    "mean platelet volume": "mpv",
    "mpv": "mpv",

    # Differential (%)
    "neutrophil": "neutrophils %",
    "neutrophils": "neutrophils %",
    "neut": "neutrophils %",
    "lymphocyte": "lymphocytes %",
    "lymphocytes": "lymphocytes %",
    "lymph": "lymphocytes %",
    "monocyte": "monocytes %",
    "monocytes": "monocytes %",
    "mono": "monocytes %",
    "eosinophil": "eosinophils %",
    "eosinophils": "eosinophils %",
    "eos": "eosinophils %",
    "basophil": "basophils %",
    "basophils": "basophils %",
    "baso": "basophils %",

    # Absolute
    "neutrophil, absolute": "absolute neutrophils",
    "neutrophils, absolute": "absolute neutrophils",
    "absolute neutrophil": "absolute neutrophils",

    "lymphocyte, absolute": "absolute lymphocytes",
    "lymphocytes, absolute": "absolute lymphocytes",
    "absolute lymphocyte": "absolute lymphocytes",

    "monocyte, absolute": "absolute monocytes",
    "monocytes, absolute": "absolute monocytes",
    "absolute monocyte": "absolute monocytes",

    "eosinophil, absolute": "absolute eosinophils",
    "eosinophils, absolute": "absolute eosinophils",
    "absolute eosinophil": "absolute eosinophils",

    "basophil, absolute": "absolute basophils",
    "basophils, absolute": "absolute basophils",
    "absolute basophil": "absolute basophils",

    # Vitamins / chemistry (examples; keep your existing ones)
    "vitamin d3": "vitamin d (25-oh)",
    "vitamin - d3": "vitamin d (25-oh)",
    "25-oh vitamin d": "vitamin d (25-oh)",
    "25-hydroxy vitamin d": "vitamin d (25-oh)",
    "uric acid": "uric acid",
}

# Light normalizer used by routes.parse -> normalize_test_name
def normalize_test_name(raw: str) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    # Remove all parentheticals and extra closing parens
    s = re.sub(r"\([^)]*\)", "", s)
    s = s.replace(")", "").replace("(", "")
    # standardize punctuation/spaces
    s = re.sub(r"[\s\-_/]+", " ", s).strip()
    # direct alias
    if s in ALIASES:
        return ALIASES[s]
    # try removing trailing words like "percentage", etc.
    s2 = s.replace(" percentage", "").replace(" percent", "")
    if s2 in ALIASES:
        return ALIASES[s2]
    # if already canonical, keep it
    if s in CANONICAL:
        return s
    return ALIASES.get(s)

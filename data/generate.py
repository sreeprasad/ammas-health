"""Generate synthetic lab reports for one fictional patient.

Writes truth JSON, clean PDFs, phone-style photos and doctor notes under data/.
Every value is invented. Re-running with the same seed gives identical output.
"""

import json
import random
import shutil
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

SEED = 20260111
ROOT = Path(__file__).resolve().parent
FONT_DIR = Path("/System/Library/Fonts/Supplemental")

CLINIC = "Amrut Clinic"
PATIENT = {"name": "Amma K. (sample patient)", "age": 68, "sex": "F", "patient_id": "SYN-0001"}
VISITS = [date(2026, 1, 8), date(2026, 3, 14), date(2026, 5, 20), date(2026, 7, 22)]
LIVE_VISIT = date(2026, 9, 12)

# id: (standard name, unit, low, high, decimals, base value, drift per visit, printed name per visit or one name)
TESTS = {
    # Hematology
    "hgb": ("Hemoglobin", "g/dL", 12.0, 15.5, 1, None, 0, ["Hemoglobin", "HGB", "Haemoglobin", "Hb", "HGB"]),
    "rbc": ("Red blood cell count", "million/µL", 4.0, 5.2, 2, 4.05, -0.05, ["RBC Count", "RBC", "Total RBC", "RBC", "RBC"]),
    "hct": ("Hematocrit", "%", 36.0, 46.0, 1, 35.4, -0.6, ["Hematocrit", "HCT", "PCV", "HCT", "HCT"]),
    "mcv": ("Mean corpuscular volume", "fL", 80.0, 100.0, 1, 84.0, -0.8, "MCV"),
    "mch": ("Mean corpuscular hemoglobin", "pg", 27.0, 33.0, 1, 28.6, -0.3, "MCH"),
    "mchc": ("Mean corpuscular hemoglobin concentration", "g/dL", 32.0, 36.0, 1, 33.1, -0.1, "MCHC"),
    "rdw_cv": ("Red cell distribution width (CV)", "%", 11.5, 14.5, 1, 13.6, 0.2, "RDW-CV"),
    "rdw_sd": ("Red cell distribution width (SD)", "fL", 39.0, 46.0, 1, 43.0, 0.4, "RDW-SD"),
    "wbc": ("White blood cell count", "10³/µL", 4.0, 11.0, 1, 6.8, 0.0, ["Total WBC Count", "WBC", "TLC", "WBC", "WBC"]),
    "neut_pct": ("Neutrophils", "%", 40.0, 75.0, 0, 58, 0, "Neutrophils"),
    "lymph_pct": ("Lymphocytes", "%", 20.0, 45.0, 0, 32, 0, "Lymphocytes"),
    "mono_pct": ("Monocytes", "%", 2.0, 10.0, 0, 6, 0, "Monocytes"),
    "eos_pct": ("Eosinophils", "%", 1.0, 6.0, 0, 3, 0, "Eosinophils"),
    "baso_pct": ("Basophils", "%", 0.0, 2.0, 0, 1, 0, "Basophils"),
    "anc": ("Absolute neutrophil count", "10³/µL", 2.0, 7.0, 2, 3.94, 0, "Abs. Neutrophil Count"),
    "alc": ("Absolute lymphocyte count", "10³/µL", 1.0, 3.0, 2, 2.18, 0, "Abs. Lymphocyte Count"),
    "amc": ("Absolute monocyte count", "10³/µL", 0.2, 1.0, 2, 0.41, 0, "Abs. Monocyte Count"),
    "aec": ("Absolute eosinophil count", "10³/µL", 0.02, 0.5, 2, 0.20, 0, "Abs. Eosinophil Count"),
    "abc": ("Absolute basophil count", "10³/µL", 0.0, 0.1, 2, 0.07, 0, "Abs. Basophil Count"),
    "plt": ("Platelet count", "10³/µL", 150.0, 410.0, 0, 248, 0, ["Platelet Count", "PLT", "Platelets", "PLT", "PLT"]),
    "mpv": ("Mean platelet volume", "fL", 7.5, 11.5, 1, 9.4, 0, "MPV"),
    "pdw": ("Platelet distribution width", "fL", 9.0, 17.0, 1, 12.8, 0, "PDW"),
    "pct": ("Plateletcrit", "%", 0.17, 0.35, 2, 0.23, 0, "PCT"),
    "esr": ("Erythrocyte sedimentation rate", "mm/hr", 0.0, 20.0, 0, 16, 0, ["ESR", "ESR (Westergren)", "ESR", "ESR", "ESR"]),
    # Coagulation
    "pt": ("Prothrombin time", "sec", 11.0, 13.5, 1, 12.4, 0, "Prothrombin Time"),
    "inr": ("INR", "", 0.8, 1.2, 2, 1.02, 0, "INR"),
    "aptt": ("Activated partial thromboplastin time", "sec", 25.0, 35.0, 1, 29.8, 0, "aPTT"),
    # Kidney and electrolytes
    "urea": ("Urea", "mg/dL", 15.0, 40.0, 0, 28, 0, ["Blood Urea", "Urea", "Serum Urea", "Urea", "Urea"]),
    "bun": ("Blood urea nitrogen", "mg/dL", 7.0, 20.0, 1, 13.1, 0, "BUN"),
    "creat": ("Creatinine", "mg/dL", 0.6, 1.1, 2, None, 0, ["Creatinine", "S. Creatinine", "Serum Creatinine", "Creat.", "S. Creatinine"]),
    "bun_creat": ("BUN/creatinine ratio", "", 10.0, 20.0, 1, 14.2, 0, "BUN/Creatinine Ratio"),
    "uric": ("Uric acid", "mg/dL", 2.4, 6.0, 1, 5.1, 0.1, ["Uric Acid", "S. Uric Acid", "Uric Acid", "Uric Acid", "Uric Acid"]),
    "na": ("Sodium", "mmol/L", 136.0, 145.0, 0, 139, 0, ["Sodium", "Na+", "Sodium", "Na", "Sodium"]),
    "k": ("Potassium", "mmol/L", 3.5, 5.1, 1, 4.3, 0, ["Potassium", "K+", "Potassium", "K", "Potassium"]),
    "cl": ("Chloride", "mmol/L", 98.0, 107.0, 0, 102, 0, ["Chloride", "Cl-", "Chloride", "Cl", "Chloride"]),
    "hco3": ("Bicarbonate", "mmol/L", 22.0, 29.0, 0, 25, 0, "Bicarbonate"),
    "ca": ("Calcium", "mg/dL", 8.6, 10.3, 1, 9.2, 0, ["Calcium", "S. Calcium", "Calcium (Total)", "Ca", "Calcium"]),
    "phos": ("Phosphorus", "mg/dL", 2.5, 4.5, 1, 3.6, 0, "Phosphorus"),
    "mg": ("Magnesium", "mg/dL", 1.7, 2.2, 1, 2.0, 0, "Magnesium"),
    "egfr": ("eGFR", "mL/min/1.73m²", 60.0, 999.0, 0, None, 0, "eGFR (CKD-EPI)"),
    # Liver
    "tbil": ("Total bilirubin", "mg/dL", 0.3, 1.2, 2, 0.68, 0, ["Bilirubin Total", "T. Bilirubin", "Total Bilirubin", "Bili (T)", "T. Bilirubin"]),
    "dbil": ("Direct bilirubin", "mg/dL", 0.0, 0.3, 2, 0.18, 0, ["Bilirubin Direct", "D. Bilirubin", "Direct Bilirubin", "Bili (D)", "D. Bilirubin"]),
    "ibil": ("Indirect bilirubin", "mg/dL", 0.2, 0.9, 2, None, 0, ["Bilirubin Indirect", "I. Bilirubin", "Indirect Bilirubin", "Bili (I)", "I. Bilirubin"]),
    "ast": ("AST", "U/L", 0.0, 35.0, 0, 24, 0, ["AST (SGOT)", "SGOT", "AST", "AST", "AST"]),
    "alt": ("ALT", "U/L", 0.0, 35.0, 0, 21, 0, ["ALT (SGPT)", "SGPT", "ALT", "ALT", "ALT"]),
    "ast_alt": ("AST/ALT ratio", "", 0.0, 2.0, 2, None, 0, "AST/ALT Ratio"),
    "alp": ("Alkaline phosphatase", "U/L", 44.0, 147.0, 0, 96, 0, ["Alkaline Phosphatase", "ALP", "Alk. Phos.", "ALP", "ALP"]),
    "ggt": ("Gamma-glutamyl transferase", "U/L", 0.0, 38.0, 0, 22, 0, ["GGT", "Gamma GT", "GGT", "GGTP", "GGT"]),
    "tprot": ("Total protein", "g/dL", 6.4, 8.3, 1, 7.1, 0, "Total Protein"),
    "alb": ("Albumin", "g/dL", 3.5, 5.2, 1, 4.1, 0, ["Albumin", "S. Albumin", "Albumin", "Alb", "Albumin"]),
    "glob": ("Globulin", "g/dL", 2.0, 3.5, 1, None, 0, "Globulin"),
    "ag_ratio": ("Albumin/globulin ratio", "", 1.0, 2.2, 2, None, 0, "A/G Ratio"),
    # Lipids
    "tc": ("Total cholesterol", "mg/dL", 0.0, 200.0, 0, None, 0, ["Total Cholesterol", "Cholesterol, Total", "T. Cholesterol", "TC", "Total Cholesterol"]),
    "tg": ("Triglycerides", "mg/dL", 0.0, 150.0, 0, 162, -6, ["Triglycerides", "TG", "Triglycerides", "TGL", "Triglycerides"]),
    "hdl": ("HDL cholesterol", "mg/dL", 40.0, 999.0, 0, 46, 1, ["HDL Cholesterol", "HDL-C", "HDL", "HDL-C", "HDL-C"]),
    "ldl": ("LDL cholesterol", "mg/dL", 0.0, 100.0, 0, None, 0, ["LDL Cholesterol", "LDL-C", "LDL (Calculated)", "LDL", "LDL-C"]),
    "vldl": ("VLDL cholesterol", "mg/dL", 5.0, 40.0, 0, None, 0, "VLDL"),
    "non_hdl": ("Non-HDL cholesterol", "mg/dL", 0.0, 130.0, 0, None, 0, "Non-HDL Cholesterol"),
    "tc_hdl": ("Total cholesterol/HDL ratio", "", 0.0, 5.0, 1, None, 0, "TC/HDL Ratio"),
    "ldl_hdl": ("LDL/HDL ratio", "", 0.0, 3.5, 1, None, 0, "LDL/HDL Ratio"),
    "tg_hdl": ("Triglyceride/HDL ratio", "", 0.0, 3.0, 1, None, 0, "TG/HDL Ratio"),
    # Cardiac and inflammation
    "hscrp": ("hs-CRP", "mg/L", 0.0, 3.0, 1, 1.2, 0, ["hs-CRP", "hsCRP", "hs-CRP", "CRP (high sensitivity)", "hs-CRP"]),
    "homocys": ("Homocysteine", "µmol/L", 5.0, 15.0, 1, 12.4, 0, "Homocysteine"),
    "lpa": ("Lipoprotein(a)", "mg/dL", 0.0, 30.0, 0, 22, 0, "Lipoprotein (a)"),
    "ck": ("Creatine kinase", "U/L", 26.0, 192.0, 0, 88, 0, "CK (Total)"),
    "ldh": ("Lactate dehydrogenase", "U/L", 140.0, 280.0, 0, 182, 0, "LDH"),
    # Endocrine and diabetes
    "tsh": ("TSH", "mIU/L", 0.4, 4.0, 1, None, 0, ["TSH", "TSH (3rd gen)", "TSH", "Thyroid Stimulating Hormone", "TSH"]),
    "ft4": ("Free T4", "ng/dL", 0.8, 1.8, 2, 1.21, 0, ["Free T4", "FT4", "Free T4", "FT4", "FT4"]),
    "ft3": ("Free T3", "pg/mL", 2.3, 4.2, 1, 3.1, 0, ["Free T3", "FT3", "Free T3", "FT3", "FT3"]),
    "t4": ("Total T4", "µg/dL", 5.0, 12.0, 1, 8.2, 0, "Total T4"),
    "t3": ("Total T3", "ng/dL", 80.0, 200.0, 0, 118, 0, "Total T3"),
    "hba1c": ("HbA1c", "%", 4.0, 5.6, 1, None, 0, ["HbA1c", "Glycated Hemoglobin", "HbA1c", "A1C", "HbA1c"]),
    "eag": ("Estimated average glucose", "mg/dL", 0.0, 117.0, 0, None, 0, "eAG"),
    "ppbs": ("Postprandial glucose", "mg/dL", 70.0, 140.0, 0, 168, 6, ["Glucose (PP)", "PPBS", "Post Prandial Glucose", "PPBS", "Glucose (PP)"]),
    "fruct": ("Fructosamine", "µmol/L", 200.0, 285.0, 0, 266, 6, "Fructosamine"),
    "fbs": ("Fasting glucose", "mg/dL", 70.0, 100.0, 0, None, 0, "Glucose (F)"),
    "cortisol": ("Cortisol (morning)", "µg/dL", 6.2, 19.4, 1, 11.8, 0, "Cortisol (AM)"),
    "pth": ("Parathyroid hormone", "pg/mL", 15.0, 65.0, 0, 71, -6, "PTH (Intact)"),
    "insulin": ("Fasting insulin", "µIU/mL", 2.6, 24.9, 1, 14.2, 0.6, "Insulin (Fasting)"),
    "cpep": ("C-peptide", "ng/mL", 1.1, 4.4, 1, 2.6, 0, "C-Peptide"),
    # Vitamins and iron
    "vitd": ("Vitamin D", "ng/mL", 30.0, 100.0, 0, None, 0, ["Vitamin D (25-OH)", "25-OH Vit D", "Vit D3", "25-Hydroxy Vitamin D", "25-OH Vit D"]),
    "b12": ("Vitamin B12", "pg/mL", 200.0, 900.0, 0, 312, -12, ["Vitamin B12", "Vit B12", "Cobalamin", "B12", "Vit B12"]),
    "folate": ("Folate", "ng/mL", 3.0, 17.0, 1, 7.4, 0, "Folate"),
    "iron": ("Serum iron", "µg/dL", 60.0, 170.0, 0, 58, -3, ["Serum Iron", "Iron", "S. Iron", "Iron", "Iron"]),
    "ferritin": ("Ferritin", "ng/mL", 15.0, 150.0, 0, 24, -2, "Ferritin"),
    "tibc": ("Total iron binding capacity", "µg/dL", 250.0, 450.0, 0, 398, 4, "TIBC"),
    "uibc": ("Unsaturated iron binding capacity", "µg/dL", 110.0, 370.0, 0, None, 0, "UIBC"),
    "tsat": ("Transferrin saturation", "%", 20.0, 50.0, 0, None, 0, "Transferrin Saturation"),
    # Urine
    "u_ph": ("Urine pH", "", 5.0, 8.0, 1, 6.0, 0, "pH"),
    "u_sg": ("Urine specific gravity", "", 1.005, 1.030, 3, 1.018, 0, "Specific Gravity"),
    "u_pus": ("Urine pus cells", "/hpf", 0.0, 5.0, 0, 2, 0, "Pus Cells"),
    "u_rbc": ("Urine red cells", "/hpf", 0.0, 2.0, 0, 1, 0, "RBC (Urine)"),
    "u_epi": ("Urine epithelial cells", "/hpf", 0.0, 5.0, 0, 2, 0, "Epithelial Cells"),
    "u_casts": ("Urine casts", "/lpf", 0.0, 2.0, 0, 0, 0, "Casts"),
    "u_crystals": ("Urine crystals", "/hpf", 0.0, 2.0, 0, 0, 0, "Crystals"),
    "u_prot": ("Urine protein", "mg/dL", 0.0, 14.0, 0, 8, 0, "Protein"),
    "u_glu": ("Urine glucose", "mg/dL", 0.0, 15.0, 0, 0, 0, "Glucose (Urine)"),
    "u_malb": ("Urine microalbumin", "mg/L", 0.0, 30.0, 1, 18.4, 1.2, "Microalbumin"),
    "u_creat": ("Urine creatinine", "mg/dL", 20.0, 320.0, 0, 96, 0, "Creatinine (Urine)"),
    "u_acr": ("Albumin/creatinine ratio", "mg/g", 0.0, 30.0, 1, None, 0, "ACR"),
    # Pancreas
    "amylase": ("Amylase", "U/L", 28.0, 100.0, 0, 64, 0, "Amylase"),
    "lipase": ("Lipase", "U/L", 13.0, 60.0, 0, 34, 0, "Lipase"),
}

# Trends the screens tell a story about: Jan, Mar, May, Jul, Sep.
HEADLINE = {
    "hba1c": [6.1, 6.4, 6.6, 6.9, 7.1],
    "hgb": [11.8, 11.4, 11.1, 10.9, 10.6],
    "ldl": [132, 124, 118, 109, 104],
    "creat": [0.92, 0.95, 0.94, 0.97, 0.96],
    "tsh": [2.1, 2.4, 2.2, 2.6, 2.3],
    "vitd": [14, 19, 24, 29, 32],
    "fbs": [None, None, None, None, 138],
}

# Genuine jumps printed clearly but blurred on the photo. A "snap to trend" rule gets these wrong.
PLANTED_JUMPS = {("hscrp", 2): 6.8, ("esr", 3): 44}

PANELS = {
    "CBC": ["hgb", "rbc", "hct", "mcv", "mch", "mchc", "rdw_cv", "rdw_sd", "wbc", "neut_pct", "lymph_pct", "mono_pct",
            "eos_pct", "baso_pct", "anc", "alc", "amc", "aec", "abc", "plt", "mpv", "pdw", "pct", "esr"],
    "COAG": ["pt", "inr", "aptt"],
    "RFT": ["urea", "bun", "creat", "bun_creat", "uric", "na", "k", "cl", "hco3", "ca", "phos", "mg", "egfr"],
    "LFT": ["tbil", "dbil", "ibil", "ast", "alt", "ast_alt", "alp", "ggt", "tprot", "alb", "glob", "ag_ratio"],
    "LIPID": ["tc", "tg", "hdl", "ldl", "vldl", "non_hdl", "tc_hdl", "ldl_hdl", "tg_hdl"],
    "CARD": ["hscrp", "homocys", "lpa", "ck", "ldh"],
    "THY": ["tsh", "ft4", "ft3", "t4", "t3"],
    "DIAB": ["hba1c", "eag", "ppbs", "fruct"],
    "HORM": ["cortisol", "pth", "insulin", "cpep"],
    "VIT": ["vitd", "b12", "folate"],
    "IRON": ["iron", "ferritin", "tibc", "uibc", "tsat"],
    "URINE": ["u_ph", "u_sg", "u_pus", "u_rbc", "u_epi", "u_casts", "u_crystals", "u_prot", "u_glu", "u_malb", "u_creat", "u_acr"],
    "PANC": ["amylase", "lipase"],
}

# Per visit: (department slug, printed title, panels)
OLDER_REPORTS = [
    [
        ("hematology", "Hematology", ["CBC"]),
        ("biochemistry", "Biochemistry", ["RFT", "LFT"]),
        ("lipid-cardiac", "Lipid profile & cardiac markers", ["LIPID", "CARD"]),
        ("endocrine", "Endocrine lab", ["THY", "DIAB"]),
        ("vitamins-iron", "Vitamins & iron studies", ["VIT", "IRON"]),
        ("urine", "Urine analysis", ["URINE"]),
    ],
    [
        ("hematology", "Hematology", ["CBC", "IRON"]),
        ("biochemistry", "Biochemistry", ["RFT", "LFT", "PANC"]),
        ("lipid", "Lipid profile", ["LIPID"]),
        ("endocrine", "Endocrine lab", ["THY", "DIAB", "HORM"]),
        ("urine-vitamins", "Urine analysis & vitamins", ["URINE", "VIT"]),
    ],
    [
        ("hematology", "Hematology", ["CBC", "IRON"]),
        ("biochemistry", "Biochemistry", ["RFT", "LFT"]),
        ("lipid-cardiac", "Lipid profile & cardiac markers", ["LIPID", "CARD"]),
        ("endocrine", "Endocrine lab", ["THY", "DIAB", "HORM"]),
        ("urine-vitamins", "Urine analysis & vitamins", ["URINE", "VIT"]),
    ],
    [
        ("hematology", "Hematology", ["CBC", "COAG"]),
        ("iron", "Iron studies", ["IRON"]),
        ("biochemistry", "Biochemistry", ["RFT", "LFT"]),
        ("lipid-cardiac", "Lipid profile & cardiac markers", ["LIPID", "CARD"]),
        ("endocrine-vitamins", "Endocrine lab & vitamins", ["THY", "DIAB", "HORM", "VIT"]),
        ("urine", "Urine analysis", ["URINE"]),
    ],
]

LIVE_PAGES = [
    ("Hematology", ["hgb", "rbc", "wbc", "plt", "hct", "mcv"]),
    ("Biochemistry", ["hba1c", "fbs", "eag", "urea", "creat", "uric"]),
    ("Lipid profile", ["tc", "tg", "hdl", "ldl", "vldl", "non_hdl"]),
    ("Endocrine & vitamins", ["tsh", "ft4", "ft3", "vitd", "b12"]),
]
LIVE_SMUDGE = ("ldl", "1?4")

EXPECTED_OLDER_VALUES = 380
EXPECTED_LIVE_VALUES = 23

NOTES = [
    {
        "note_id": "note-2026-01-08",
        "date": "2026-01-08",
        "department": "General Medicine",
        "doctor": "Dr. R. Example",
        "text": "Routine review. Vitamin D low at 14 ng/mL. Start vitamin D. Retest in 3 months. "
                "HbA1c 6.1%, borderline; continue walking daily. Hemoglobin 11.8 g/dL, slightly low; no symptoms reported.",
    },
    {
        "note_id": "note-2026-03-14",
        "date": "2026-03-14",
        "department": "Endocrinology",
        "doctor": "Dr. S. Example",
        "text": "HbA1c up to 6.4% from 6.1%. Recheck HbA1c in 2 months. Diet review suggested; family to book a session. "
                "Vitamin D improving at 19 ng/mL on supplements. Thyroid steady.",
    },
    {
        "note_id": "note-2026-05-20",
        "date": "2026-05-20",
        "department": "Endocrinology",
        "doctor": "Dr. S. Example",
        "text": "HbA1c recheck 6.6%, still rising slowly. Continue current routine. "
                "Endocrinology review booked for Oct 22 with fresh labs in September.",
    },
    {
        "note_id": "note-2026-07-22",
        "date": "2026-07-22",
        "department": "General Medicine",
        "doctor": "Dr. R. Example",
        "text": "Mild tiredness. Watch. Hemoglobin 10.9 g/dL, lower than in March. ESR raised at 44 after a recent cold; "
                "repeat with next labs. LDL 109 mg/dL, improving.",
    },
    {
        "note_id": "note-2026-09-12",
        "date": "2026-09-12",
        "department": "Laboratory",
        "doctor": "Lab desk",
        "text": "Fasting sample collected for the Oct 22 Endocrinology review. Fasting glucose added to the panel this time.",
    },
]

FOLLOWUPS_EXPECTED = [
    {"from_note": "note-2026-01-08", "said_on": "2026-01-08", "text": "Start vitamin D. Retest in 3 months.", "test": "vitd", "due": "2026-04-08"},
    {"from_note": "note-2026-03-14", "said_on": "2026-03-14", "text": "Recheck HbA1c in 2 months.", "test": "hba1c", "due": "2026-05-14"},
    {"from_note": "note-2026-03-14", "said_on": "2026-03-14", "text": "Diet review suggested.", "test": None, "due": None},
    {"from_note": "note-2026-07-22", "said_on": "2026-07-22", "text": "Mild tiredness. Watch.", "test": "hgb", "due": None},
    {"from_note": "note-2026-05-20", "said_on": "2026-05-20", "text": "Endocrinology review booked for Oct 22.", "test": None, "due": "2026-10-22"},
]

PAGE_W, PAGE_H = 1240, 1754
ROWS_PER_PAGE = 16
ROW_H = 58
TABLE_TOP = 560
COLS = {"test": 80, "result": 560, "flag": 720, "unit": 800, "range": 1000}
INK = (26, 26, 26)
MUTED = (96, 96, 96)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


F_TITLE = font("Georgia.ttf", 46)
F_BODY = font("Arial.ttf", 24)
F_BOLD = font("Arial Bold.ttf", 24)
F_SMALL = font("Arial.ttf", 19)
F_RESULT = font("Courier New Bold.ttf", 28)
F_MARK = font("Arial Bold.ttf", 20)


def fmt(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def printed_name(test_id: str, visit_index: int) -> str:
    names = TESTS[test_id][7]
    return names[visit_index] if isinstance(names, list) else names


def range_text(test_id: str) -> str:
    _, unit, low, high, d, *_ = TESTS[test_id]
    if high >= 999:
        return f"> {fmt(low, d)}"
    if low == 0:
        return f"< {fmt(high, d)}"
    return f"{fmt(low, d)} - {fmt(high, d)}"


def flag(test_id: str, value: float) -> str:
    _, _, low, high, *_ = TESTS[test_id]
    if value < low:
        return "L"
    if value > high:
        return "H"
    return ""


def simulate_values(rng: random.Random) -> list[dict]:
    """One dict of test -> value per visit, Jan..Sep, with derived values kept consistent."""
    visits = []
    for i in range(5):
        v = {}
        for tid, (_, _, low, high, d, base, drift, _) in TESTS.items():
            if tid in HEADLINE:
                v[tid] = HEADLINE[tid][i]
            elif base is not None:
                spread = max(abs(base) * 0.04, 10 ** -d)
                v[tid] = round(base + drift * i + rng.uniform(-spread, spread), d)
        v["esr"] = round(rng.uniform(15, 19))
        v["hscrp"] = round(rng.uniform(0.9, 1.4), 1)
        for (tid, idx), val in PLANTED_JUMPS.items():
            if idx == i:
                v[tid] = val

        v["hct"] = round(v["hgb"] * 3.05 + rng.uniform(-0.4, 0.4), 1)
        v["bun"] = round(v["urea"] / 2.14, 1)
        v["bun_creat"] = round(v["bun"] / v["creat"], 1)
        v["egfr"] = round(62 / v["creat"] - 2)
        v["ibil"] = round(v["tbil"] - v["dbil"], 2)
        v["ast_alt"] = round(v["ast"] / v["alt"], 2)
        v["glob"] = round(v["tprot"] - v["alb"], 1)
        v["ag_ratio"] = round(v["alb"] / v["glob"], 2)
        v["vldl"] = round(v["tg"] / 5)
        v["tc"] = round(v["ldl"] + v["hdl"] + v["vldl"])
        v["non_hdl"] = v["tc"] - v["hdl"]
        v["tc_hdl"] = round(v["tc"] / v["hdl"], 1)
        v["ldl_hdl"] = round(v["ldl"] / v["hdl"], 1)
        v["tg_hdl"] = round(v["tg"] / v["hdl"], 1)
        v["eag"] = round(28.7 * v["hba1c"] - 46.7)
        v["uibc"] = round(v["tibc"] - v["iron"])
        v["tsat"] = round(100 * v["iron"] / v["tibc"])
        v["u_acr"] = round(100 * v["u_malb"] / v["u_creat"], 1)
        visits.append(v)
    return visits


def draw_header(draw: ImageDraw.ImageDraw, visit: date, title: str, page: int, pages: int) -> None:
    draw.rectangle([0, 0, PAGE_W, 150], fill=(232, 240, 236))
    draw.text((80, 40), CLINIC, font=F_TITLE, fill=(20, 70, 60))
    draw.text((80, 100), "Department of Laboratory Medicine · 14 Example Road, Sampletown", font=F_SMALL, fill=MUTED)
    draw.text((PAGE_W - 80, 52), "SYNTHETIC SAMPLE", font=F_MARK, fill=(170, 40, 30), anchor="ra")
    draw.text((PAGE_W - 80, 80), "NOT A REAL PATIENT", font=F_MARK, fill=(170, 40, 30), anchor="ra")

    rows = [
        ("Patient", PATIENT["name"], "Patient ID", PATIENT["patient_id"]),
        ("Age / Sex", f"{PATIENT['age']} / {PATIENT['sex']}", "Collected", visit.strftime("%d-%b-%Y")),
        ("Report", title, "Page", f"{page} of {pages}"),
    ]
    y = 200
    for k1, v1, k2, v2 in rows:
        draw.text((80, y), f"{k1}:", font=F_BOLD, fill=INK)
        draw.text((240, y), v1, font=F_BODY, fill=INK)
        draw.text((760, y), f"{k2}:", font=F_BOLD, fill=INK)
        draw.text((920, y), v2, font=F_BODY, fill=INK)
        y += 44
    draw.line([80, 360, PAGE_W - 80, 360], fill=(180, 180, 180), width=2)
    draw.text((80, 400), title.upper(), font=F_BOLD, fill=(20, 70, 60))

    hy = TABLE_TOP - 70
    for key, label in [("test", "Test"), ("result", "Result"), ("flag", "Flag"), ("unit", "Units"), ("range", "Ref. range")]:
        draw.text((COLS[key], hy), label, font=F_BOLD, fill=INK)
    draw.line([80, hy + 40, PAGE_W - 80, hy + 40], fill=INK, width=2)


def draw_footer(draw: ImageDraw.ImageDraw) -> None:
    draw.line([80, PAGE_H - 170, PAGE_W - 80, PAGE_H - 170], fill=(180, 180, 180), width=1)
    draw.text((80, PAGE_H - 150), "Verified by: Dr. A. Example, MD (Pathology)", font=F_SMALL, fill=MUTED)
    draw.text((80, PAGE_H - 115), "Synthetic data generated for a hackathon demo. Not for clinical use.", font=F_SMALL, fill=MUTED)


def render_page(visit: date, title: str, page: int, pages: int, rows: list[dict]) -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(img)
    draw_header(draw, visit, title, page, pages)
    y = TABLE_TOP
    for row in rows:
        if row["flag"]:
            draw.rectangle([80, y - 8, PAGE_W - 80, y + ROW_H - 18], fill=(248, 244, 236))
        draw.text((COLS["test"], y), row["printed_name"], font=F_BODY, fill=INK)
        bbox = draw.textbbox((COLS["result"], y - 2), row["value_text"], font=F_RESULT)
        draw.text((COLS["result"], y - 2), row["value_text"], font=F_RESULT, fill=INK)
        draw.text((COLS["flag"], y), row["flag"], font=F_BOLD, fill=(170, 40, 30))
        draw.text((COLS["unit"], y), row["unit"], font=F_BODY, fill=INK)
        draw.text((COLS["range"], y), row["range"]["text"], font=F_BODY, fill=INK)
        pad = 6
        row["box"] = [
            round((bbox[0] - pad) / PAGE_W, 4),
            round((bbox[1] - pad) / PAGE_H, 4),
            round((bbox[2] + pad) / PAGE_W, 4),
            round((bbox[3] + pad) / PAGE_H, 4),
        ]
        row["_px"] = bbox
        y += ROW_H
    draw_footer(draw)
    return img


def apply_defect(img: Image.Image, row: dict) -> None:
    x0, y0, x1, y1 = row["_px"]
    if row.get("defect") == "blur":
        region = (x0 - 10, y0 - 10, x1 + 10, y1 + 10)
        img.paste(img.crop(region).filter(ImageFilter.GaussianBlur(3.2)), region[:2])
    elif row.get("defect") == "smudge":
        draw = ImageDraw.Draw(img)
        digit_left = x0 + F_RESULT.getlength(row["value_text"][:1])
        digit_right = x0 + F_RESULT.getlength(row["value_text"][:2])
        draw.ellipse([digit_left - 1, y0 - 4, digit_right + 1, y1 + 4], fill=(150, 142, 130))
        region = (int(digit_left) - 2, y0 - 8, int(digit_right) + 2, y1 + 8)
        img.paste(img.crop(region).filter(ImageFilter.GaussianBlur(2.5)), region[:2])


def to_photo(page: Image.Image, rng: random.Random) -> tuple[Image.Image, dict]:
    angle = rng.uniform(-3.5, 3.5)
    shrink = rng.uniform(0.015, 0.035)
    w, h = page.size
    canvas = Image.new("RGB", (w + 160, h + 160), (92, 76, 60))
    canvas.paste(page, (80, 80))
    rotated = canvas.rotate(angle, resample=Image.BICUBIC, fillcolor=(92, 76, 60))
    cw, ch = rotated.size
    dx = cw * shrink
    quad = (dx, 0, 0, ch, cw, ch, cw - dx, 0)
    warped = rotated.transform((cw, ch), Image.QUAD, quad, resample=Image.BICUBIC)
    photo = warped.resize((cw * 1000 // cw, ch * 1000 // cw), Image.LANCZOS)
    photo = photo.filter(ImageFilter.GaussianBlur(0.6))

    shade = Image.linear_gradient("L").resize(photo.size).rotate(rng.choice([0, 90, 180, 270]))
    photo = Image.composite(photo, ImageEnhance.Brightness(photo).enhance(0.78), shade)
    noise = Image.effect_noise(photo.size, 18).convert("RGB")
    photo = Image.blend(photo, noise, 0.06)
    return photo, {"rotate_deg": round(angle, 2), "keystone": round(shrink, 3), "margin_px": 80, "width_px": 1000}


def build_report(key: str, visit: date, visit_index: int, title: str, pages_spec: list[tuple[str, list[str]]],
                 values: dict, rng: random.Random, live: bool) -> dict:
    out_pdf = ROOT / "reports" / "pdf" / f"{key}.pdf"
    page_images, photos, truth_values = [], [], []
    pages = len(pages_spec)
    for page_no, (page_title, test_ids) in enumerate(pages_spec, start=1):
        rows = []
        for tid in test_ids:
            name, unit, low, high, d, *_ = TESTS[tid]
            value = values[tid]
            row = {
                "test": tid,
                "standard_name": name,
                "printed_name": printed_name(tid, visit_index),
                "value": value,
                "value_text": fmt(value, d),
                "unit": unit,
                "range": {"low": low, "high": None if high >= 999 else high, "text": range_text(tid)},
                "flag": flag(tid, value),
                "page": page_no,
            }
            if (tid, visit_index) in PLANTED_JUMPS:
                row["defect"] = "blur"
                row["planted_jump"] = True
            if live and tid == LIVE_SMUDGE[0]:
                row["defect"] = "smudge"
                row["photo_reads_as"] = LIVE_SMUDGE[1]
            rows.append(row)

        clean = render_page(visit, page_title, page_no, pages, rows)
        page_images.append(clean)
        damaged = clean.copy()
        for row in rows:
            apply_defect(damaged, row)
        photo, transform = to_photo(damaged, rng)
        photo_name = f"{key}_p{page_no}.jpg"
        photo.save(ROOT / "reports" / "photo" / photo_name, quality=78)
        photos.append({"page": page_no, "file": f"reports/photo/{photo_name}", "transform": transform})
        for row in rows:
            row.pop("_px")
        truth_values.extend(rows)

    page_images[0].save(out_pdf, save_all=True, append_images=page_images[1:], resolution=150)
    return {
        "report_key": key,
        "synthetic": True,
        "patient_id": PATIENT["patient_id"],
        "clinic": CLINIC,
        "visit_date": visit.isoformat(),
        "title": title,
        "pages": pages,
        "files": {"pdf": f"reports/pdf/{key}.pdf", "photos": photos},
        "box_space": "normalized to the clean page, [x0, y0, x1, y1]",
        "values": truth_values,
    }


def chunk_pages(title: str, test_ids: list[str]) -> list[tuple[str, list[str]]]:
    return [(title, test_ids[i:i + ROWS_PER_PAGE]) for i in range(0, len(test_ids), ROWS_PER_PAGE)]


def main() -> None:
    rng = random.Random(SEED)
    for sub in ["truth", "reports/pdf", "reports/photo", "notes"]:
        target = ROOT / sub
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)

    values = simulate_values(rng)
    manifest, older_count = [], 0

    for visit_index, (visit, reports) in enumerate(zip(VISITS, OLDER_REPORTS)):
        for slug, title, panels in reports:
            key = f"{visit.isoformat()}_{slug}"
            test_ids = [t for p in panels for t in PANELS[p]]
            truth = build_report(key, visit, visit_index, title, chunk_pages(title, test_ids), values[visit_index], rng, live=False)
            older_count += len(truth["values"])
            (ROOT / "truth" / f"{key}.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
            manifest.append({"report_key": key, "visit_date": truth["visit_date"], "title": title, "values": len(truth["values"]),
                             "pages": truth["pages"], "live": False})

    live_key = f"{LIVE_VISIT.isoformat()}_full-panel"
    live = build_report(live_key, LIVE_VISIT, 4, "Full panel", LIVE_PAGES, values[4], rng, live=True)
    (ROOT / "truth" / f"{live_key}.json").write_text(json.dumps(live, indent=2, ensure_ascii=False))
    manifest.append({"report_key": live_key, "visit_date": live["visit_date"], "title": "Full panel", "values": len(live["values"]),
                     "pages": live["pages"], "live": True})

    for note in NOTES:
        (ROOT / "notes" / f"{note['note_id']}.json").write_text(json.dumps({**note, "synthetic": True}, indent=2, ensure_ascii=False))
    (ROOT / "notes" / "followups_expected.json").write_text(json.dumps(FOLLOWUPS_EXPECTED, indent=2))
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    older_reports = sum(1 for m in manifest if not m["live"])
    assert older_reports == 22, older_reports
    assert older_count == EXPECTED_OLDER_VALUES, older_count
    assert len(live["values"]) == EXPECTED_LIVE_VALUES, len(live["values"])
    print(f"older: {older_reports} reports, {older_count} values · live: {live_key}, {len(live['values'])} values")
    print(f"notes: {len(NOTES)} · follow-ups expected: {len(FOLLOWUPS_EXPECTED)}")


if __name__ == "__main__":
    main()

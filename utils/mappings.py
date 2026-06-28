"""NDC -> Product group mapping and wholesaler classification.

NDC values arrive in several shapes (clean 11-digit strings, pandas-read
floats like 66794024942.0, and the occasional non-numeric item code such as
'PIR030'). Everything that is not a known numeric NDC is bucketed as
"UNMAPPED" rather than silently dropped.
"""
import re

NDC_TO_PROD = {
    "66794015701": "GABLOFEN", "66794015702": "GABLOFEN", "66794015101": "GABLOFEN",
    "66794015502": "GABLOFEN", "66794015602": "GABLOFEN", "66794015501": "GABLOFEN",
    "66794015601": "GABLOFEN", "66794025841": "Pantoprazole",
    "66794023741": "DOXYCYCLINE", "66794020541": "GLYCOPYRROLATE",
    "66794020342": "GLYCOPYRROLATE", "66794020242": "GLYCOPYRROLATE",
    "66794020442": "GLYCOPYRROLATE", "66794024942": "CHLORPROMAZINE",
    "66794025042": "CHLORPROMAZINE", "66794001525": "SEVOFLURANE",
    "66794002225": "NOVA-SEVOFLURANE", "66794001725": "ISOFLURANE",
    "66794001710": "ISOFLURANE", "66794001925": "NOVA-ISOFLURANE",
    "66794001910": "NOVA-ISOFLURANE", "66794025542": "Zinc Sulfate",
    "66794023942": "Zinc Sulfate", "66794024042": "Zinc Sulfate",
    "66794021943": "LINEZOLID", "66794023643": "NOVA-LINEZOLID",
    "66794023042": "DEXMED", "66794023541": "DEXMED",
    "66794023342": "NOVA-DEXMED", "66794023444": "DEXMED",
    "66794022841": "ROCURONIUM", "66794022941": "ROCURONIUM",
    "66794016002": "MITIGO", "66794016202": "MITIGO",
    "66794025964": "EDARAVONE", "66794023242": "SUCCINYCHOLINE",
    "66794001310": "ISOFLURANE", "66794001325": "ISOFLURANE",
}

WHOLESALER_GROUPS = ["ABC", "Cardinal", "Mckesson", "Mckesson Medical", "Others"]

UNMAPPED = "UNMAPPED"


def normalize_ndc(value):
    """Return a valid NDC digit string (>=10 digits), or None.

    Rejects item codes like 'PIR030' whose digit residue is too short to be a
    real NDC.
    """
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    digits = re.sub(r"\D", "", s)
    return digits if len(digits) >= 10 else None


def ndc_to_product(value):
    """Map any NDC-like value to a product group, or 'UNMAPPED'."""
    ndc = normalize_ndc(value)
    if ndc is None:
        return UNMAPPED
    return NDC_TO_PROD.get(ndc, UNMAPPED)


def classify_wholesaler(name):
    """Bucket a free-text wholesaler name into one of WHOLESALER_GROUPS."""
    n = str(name).upper()
    if "MCKESSON MEDICAL" in n or "MCKESSON MED" in n:
        return "Mckesson Medical"
    if "MCKESSON" in n:
        return "Mckesson"
    if "CARDINAL" in n:
        return "Cardinal"
    if "ABC" in n or "AMERISOURCE" in n or "CENCORA" in n:
        return "ABC"
    return "Others"

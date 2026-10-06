"""Typed-extract helpers. Transform of codes and amounts happens here, before SQL."""

from __future__ import annotations

DIAGNOSIS_NAME = {
    "I50.9": "Heart failure",
    "E11.9": "Type 2 diabetes",
    "J18.9": "Pneumonia",
    "N18.6": "End-stage renal disease",
    "I21.9": "Acute myocardial infarction",
    "J44.1": "COPD with exacerbation",
    "A41.9": "Sepsis",
    "K92.2": "GI hemorrhage",
}
PAYER_ALIASES = {
    "pm-jay": "PM-JAY",
    "pmjay": "PM-JAY",
    "ayushman bharat": "PM-JAY",
    "cghs": "CGHS",
    "esic": "ESIC",
    "private": "Private insurance",
    "private insurance": "Private insurance",
    "self-pay": "Self-pay",
    "self pay": "Self-pay",
}


def parse_money(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text == "" or text.lower() == "nan":
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def clean_code(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if text in DIAGNOSIS_NAME:
        return text
    return None


def clean_payer(value: object) -> str | None:
    text = " ".join(str(value or "").split()).lower()
    return PAYER_ALIASES.get(text)

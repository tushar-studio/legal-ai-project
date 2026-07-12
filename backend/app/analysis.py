"""Deterministic legal-text processing used by the local ingestion pipeline."""
import re


LEGAL_TERMS = (
    "appeal", "arbitration", "bail", "breach", "compensation", "constitutional",
    "contract", "damages", "defamation", "evidence", "fundamental rights",
    "injunction", "jurisdiction", "limitation", "petition", "precedent", "writ",
)


def split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"(?:\r?\n\s*){2,}", text)
    return [re.sub(r"\s+", " ", part).strip() for part in parts if len(re.sub(r"\s+", " ", part).strip()) >= 80]


def classify_paragraph(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("held that", "we hold", "it is held", "therefore held")):
        return "Holding"
    if any(term in lowered for term in ("issue", "question is", "whether")):
        return "Legal Issue"
    if any(term in lowered for term in ("submitted", "contended", "argued")):
        return "Arguments"
    if any(term in lowered for term in ("section", "article", "act", "statute")):
        return "Legal Provision"
    if any(term in lowered for term in ("facts", "background", "petitioner", "respondent")):
        return "Facts"
    return "Analysis"


def analyze_paragraph(text: str) -> dict:
    lowered = text.lower()
    terms = [term.title() for term in LEGAL_TERMS if term in lowered]
    articles = sorted(set(re.findall(r"\bArticle\s+\d+(?:\s*\([^)]+\))*", text, flags=re.IGNORECASE)), key=str.lower)
    acts = sorted(set(re.findall(r"\b[A-Z][A-Za-z,&\- ]{2,80}\s+Act(?:,?\s+\d{4})?", text)))
    cases = sorted(set(re.findall(r"\b[A-Z][A-Za-z.&' ]{1,60}\s+v(?:s\.?|\.)\s+[A-Z][A-Za-z.&' ]{1,60}", text)))
    return {"classification": classify_paragraph(text), "legal_terms": terms, "referenced_articles": articles, "referenced_acts": acts, "referenced_cases": cases}

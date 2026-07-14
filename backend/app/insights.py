"""Source-grounded concise legal insights with an optional OpenAI-compatible LLM hook."""
import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

SECTION_KEYS = (
    "overview", "facts", "issues", "arguments", "judgment",
    "ratio_decidendi", "obiter_dicta", "final_decision",
)

SECTION_TERMS = {
    "facts": ("petitioner", "respondent", "filed", "challenged", "background"),
    "issues": ("whether", "issue", "question", "validity"),
    "arguments": ("submitted", "contended", "argued", "counsel", "urged"),
    "judgment": ("held", "conclude", "therefore", "decided", "order"),
    "ratio_decidendi": ("held", "we hold", "principle", "settled", "binding", "ratio"),
    "obiter_dicta": ("observe", "observation", "however", "clarify", "may be noted"),
    "final_decision": ("appeal is allowed", "appeal is dismissed", "petition is allowed", "petition is dismissed", "disposed of", "accordingly"),
}


def _sentences(text: str, limit: int = 4) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [part.strip() for part in parts if len(part.strip()) >= 30][:limit]


def _compact(text: str, limit: int = 4) -> str:
    sentences = _sentences(text, limit)
    return " ".join(sentences) if sentences else "The source does not provide enough readable text for a concise summary."


def _ranked_source(paragraphs: list[dict], terms: tuple[str, ...], fallback_text: str) -> str:
    ranked = sorted(
        paragraphs,
        key=lambda item: sum(term in item["original_text"].lower() for term in terms),
        reverse=True,
    )
    matches = [item["original_text"] for item in ranked if any(term in item["original_text"].lower() for term in terms)]
    return " ".join(matches[:3]) if matches else fallback_text


def deterministic_insights(paragraphs: list[dict], full_text: str) -> dict:
    """Concise, deterministic fallback that never adds facts absent from source text."""
    classified = {}
    for item in paragraphs:
        classified.setdefault(item["classification"], []).append(item["original_text"])
    dates = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", full_text)))[:4]
    facts_source = " ".join(classified.get("Facts", [])) or _ranked_source(paragraphs, SECTION_TERMS["facts"], full_text)
    issues_source = " ".join(classified.get("Legal Issue", [])) or _ranked_source(paragraphs, SECTION_TERMS["issues"], full_text)
    result = {
        "overview": "\n".join((
            f"• Key Dates: {', '.join(dates) if dates else 'Not clearly stated in the retrieved source.'}",
            f"• Core Matter: {_compact(facts_source, 1)}",
            f"• Legal Challenge: {_compact(issues_source, 1)}",
        )),
        "facts": _compact(facts_source, 4),
        "issues": _compact(issues_source, 4),
    }
    for key in ("arguments", "judgment", "ratio_decidendi", "obiter_dicta", "final_decision"):
        result[key] = _compact(_ranked_source(paragraphs, SECTION_TERMS[key], full_text), 4)
    result["mode"] = "deterministic-source-grounded"
    return result


def _llm_settings() -> tuple[str, str, str] | None:
    base_url = os.getenv("LEGAL_LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LEGAL_LLM_API_KEY", "")
    model = os.getenv("LEGAL_LLM_MODEL", "")
    return (base_url, api_key, model) if base_url and api_key and model else None


def _llm_insights(title: str, paragraphs: list[dict]) -> dict | None:
    settings = _llm_settings()
    if not settings:
        return None
    base_url, api_key, model = settings
    # Representative, classified passages keep the LLM input bounded while the
    # full source continues to be available through the paragraph API.
    source_packet = "\n\n".join(f"[{item['classification']}] {item['original_text']}" for item in paragraphs[:80])
    prompt = (
        "Return JSON only. Summarise only the supplied Indian judgment passages; do not infer missing facts. "
        "For overview use exactly Key Dates, Core Matter and Legal Challenge bullets. "
        "For facts, issues, arguments, judgment, ratio_decidendi, obiter_dicta and final_decision use 3-4 concise sentences each. "
        f"Required JSON keys: {', '.join(SECTION_KEYS)}.\nCase: {title}\n\nSource passages:\n{source_packet}"
    )
    payload = json.dumps({"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "You are a source-grounded Indian legal research summariser."}, {"role": "user", "content": prompt}]}).encode("utf-8")
    request = Request(f"{base_url}/chat/completions", data=payload, method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            content = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"]
        data = json.loads(content)
        if not all(isinstance(data.get(key), str) and data[key].strip() for key in SECTION_KEYS):
            raise ValueError("LLM response omitted a required insight field")
        data["mode"] = "llm-source-grounded"
        return data
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Legal insight LLM failed; using deterministic fallback: %s", exc)
        return None


def build_case_insights(title: str, paragraphs: list[dict], full_text: str) -> dict:
    return _llm_insights(title, paragraphs) or deterministic_insights(paragraphs, full_text)

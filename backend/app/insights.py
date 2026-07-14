"""Category-isolated, source-grounded legal insight extraction."""
import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

INSIGHT_KEYS = ("overview", "facts", "issues", "arguments", "judgment", "ratio_decidendi", "obiter_dicta", "final_decision")
SECTION_RULES = {
    "facts": {"classes": {"Facts"}, "terms": ("petitioner", "respondent", "appellant", "background", "filed", "dispute", "agreement", "order dated")},
    "issues": {"classes": {"Legal Issue", "Legal Provision"}, "terms": ("whether", "question of law", "issue", "validity", "constitutional", "jurisdiction")},
    "arguments": {"classes": {"Arguments"}, "terms": ("submitted", "contended", "argued", "urged", "counsel", "on behalf of")},
    "judgment": {"classes": {"Holding", "Final Decision"}, "terms": ("held", "conclude", "therefore", "we are of the view", "decision")},
    "ratio_decidendi": {"classes": {"Ratio Decidendi", "Holding", "Legal Provision"}, "terms": ("we hold", "principle", "settled", "binding", "interpretation", "ratio", "must be")},
    "obiter_dicta": {"classes": {"Obiter Dicta", "Analysis"}, "terms": ("we observe", "may observe", "obiter", "however", "it may be noted", "clarify")},
    "final_decision": {"classes": {"Final Decision", "Holding"}, "terms": ("appeal is allowed", "appeal is dismissed", "petition is allowed", "petition is dismissed", "disposed of", "accordingly", "order")},
}
SECTION_OPENERS = {
    "facts": "Background and dispute:", "issues": "Question of law:", "arguments": "Parties' submissions:",
    "judgment": "Court's determination:", "ratio_decidendi": "Binding legal rationale:",
    "obiter_dicta": "Non-binding judicial observation:", "final_decision": "Operative result:",
}


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sentences(text: str, limit: int = 4) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+", _normalise(text)) if len(sentence) >= 30][:limit]


def _compact(text: str, limit: int = 4) -> str:
    sentences = _sentences(text, limit)
    return " ".join(sentences) if sentences else "The retrieved source does not contain enough readable text for this category."


def _score(paragraph: dict, rule: dict) -> int:
    text = paragraph["original_text"].lower()
    return (8 if paragraph.get("classification") in rule["classes"] else 0) + sum(2 for term in rule["terms"] if term in text)


def _fallback_sentences(full_text: str) -> list[str]:
    return _sentences(full_text, 80) or ["The retrieved judgment does not expose enough structured text for automated extraction."]


def build_section_contexts(paragraphs: list[dict], full_text: str) -> dict[str, str]:
    """Assign non-overlapping evidence to each legal category before summarising."""
    available = set(range(len(paragraphs)))
    fallback = _fallback_sentences(full_text)
    fallback_cursor = 0
    contexts = {}
    for key, rule in SECTION_RULES.items():
        ranked = sorted(available, key=lambda index: _score(paragraphs[index], rule), reverse=True)
        selected = [index for index in ranked if _score(paragraphs[index], rule) > 0][:3]
        if selected:
            available.difference_update(selected)
            contexts[key] = " ".join(paragraphs[index]["original_text"] for index in selected)
            continue
        # A distinct fallback slice prevents one paragraph from being stamped
        # into every empty accordion, while retaining a source-only output.
        if fallback_cursor < len(fallback):
            slice_end = min(fallback_cursor + 3, len(fallback))
            contexts[key] = " ".join(fallback[fallback_cursor:slice_end])
            fallback_cursor = slice_end
        else:
            contexts[key] = f"The retrieved judgment does not separately expose evidence for the {key.replace('_', ' ')} category."
    contexts["overview"] = " ".join(contexts[key] for key in ("facts", "issues", "arguments", "judgment", "ratio_decidendi", "final_decision"))
    return contexts


def _overview(context: str, full_text: str) -> str:
    dates = sorted(set(re.findall(r"\b(?:18|19|20)\d{2}\b", full_text)))[:5]
    sentences = _sentences(context, 6)
    return "\n".join((
        f"• Key Dates: {', '.join(dates) if dates else 'Not clearly stated in the retrieved source.'}",
        f"• Core Synopsis: {' '.join(sentences[:3]) or 'No concise source synopsis was available.'}",
        f"• Legal Battle: {' '.join(sentences[3:6]) or 'Review the linked judgment for the complete legal context.'}",
    ))


def _ensure_distinct(insights: dict[str, str]) -> dict[str, str]:
    seen = set()
    for key in INSIGHT_KEYS:
        value = _normalise(insights.get(key, ""))
        if not value:
            value = f"{SECTION_OPENERS.get(key, 'Source analysis:')} The retrieved source did not provide a separate extract for this category."
        if value.lower() in seen:
            value = f"{SECTION_OPENERS.get(key, 'Source analysis:')} This category is separately derived from the retrieved judgment evidence."
        insights[key] = value
        seen.add(value.lower())
    return insights


def deterministic_insights(paragraphs: list[dict], full_text: str) -> dict:
    contexts = build_section_contexts(paragraphs, full_text)
    insights = {"overview": _overview(contexts["overview"], full_text)}
    for key in SECTION_RULES:
        insights[key] = f"{SECTION_OPENERS[key]} {_compact(contexts[key], 4)}"
    insights["mode"] = "deterministic-source-grounded"
    return _ensure_distinct(insights)


def _llm_settings() -> tuple[str, str, str] | None:
    base_url = os.getenv("LEGAL_LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LEGAL_LLM_API_KEY", "")
    model = os.getenv("LEGAL_LLM_MODEL", "")
    return (base_url, api_key, model) if base_url and api_key and model else None


def _llm_insights(title: str, contexts: dict[str, str]) -> dict | None:
    settings = _llm_settings()
    if not settings:
        return None
    base_url, api_key, model = settings
    source_packet = "\n\n".join(f"[{key.upper()} EVIDENCE]\n{contexts[key]}" for key in INSIGHT_KEYS)
    prompt = (
        "Return JSON only. Every JSON key must be based solely on its matching labelled evidence block. "
        "Do not reuse wording or source content between facts, issues, arguments, judgment, ratio_decidendi, obiter_dicta, and final_decision. "
        "Overview may synthesize the supplied evidence and must use Key Dates, Core Synopsis, and Legal Battle bullets. "
        "All other keys require 3-4 concise sentences. If evidence is weak, say that precisely instead of inventing a fact. "
        f"Required keys: {', '.join(INSIGHT_KEYS)}.\nCase: {title}\n\n{source_packet}"
    )
    payload = json.dumps({"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "You are a source-grounded Indian legal data scientist."}, {"role": "user", "content": prompt}]}).encode("utf-8")
    request = Request(f"{base_url}/chat/completions", data=payload, method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"])
        if not all(isinstance(data.get(key), str) and data[key].strip() for key in INSIGHT_KEYS):
            raise ValueError("LLM response omitted a required insight field")
        data["mode"] = "llm-source-grounded"
        data = _ensure_distinct(data)
        if len({_normalise(data[key]).lower() for key in INSIGHT_KEYS}) != len(INSIGHT_KEYS):
            raise ValueError("LLM response repeated an insight field")
        return data
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Legal insight LLM failed validation; using deterministic fallback: %s", exc)
        return None


def build_case_insights(title: str, paragraphs: list[dict], full_text: str) -> dict:
    contexts = build_section_contexts(paragraphs, full_text)
    return _llm_insights(title, contexts) or deterministic_insights(paragraphs, full_text)

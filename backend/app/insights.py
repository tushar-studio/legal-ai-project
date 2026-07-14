"""Source-grounded, non-duplicative bullet insight extraction for legal dashboards."""
import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .analysis import extract_legal_signals

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

DEFAULT_BULLETS = {
    "facts": ["Factual record: the retrieved judgment does not separately state a fuller factual narrative.", "Case context: review the linked original judgment for the complete chronology."],
    "issues": ["Question of law: the retrieved text does not expressly frame a separate issue.", "Legal scope: the linked source should be reviewed for the court's complete formulation."],
    "arguments": ["Party submissions: the retrieved text does not separately attribute detailed assertions to each side.", "Advocacy record: review the linked judgment for the full submissions of the parties."],
    "judgment": ["Court determination: the retrieved text does not expose a separate determination passage.", "Outcome context: consult the linked judgment for the complete reasoning and order."],
    "ratio_decidendi": ["Binding rationale: no distinct ratio passage was identified in the retrieved source.", "Legal rule: review the linked judgment before treating any proposition as binding."],
    "obiter_dicta": ["Judicial observation: no separate non-binding observation was identified in the retrieved text.", "Interpretive context: any broader remark should be verified against the linked judgment."],
    "final_decision": ["Operative result: the retrieved source does not expose a separate dispositive paragraph.", "Order verification: review the linked judgment for the authoritative final direction."],
}


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sentences(text: str, limit: int = 5) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+", _normalise(text)) if len(sentence) >= 30][:limit]


def _score(paragraph: dict, rule: dict) -> int:
    text = paragraph["original_text"].lower()
    return (8 if paragraph.get("classification") in rule["classes"] else 0) + sum(2 for term in rule["terms"] if term in text)


def build_section_contexts(paragraphs: list[dict], full_text: str) -> dict[str, str]:
    """Allocate paragraph evidence once; no evidence block is shared across sections."""
    available = set(range(len(paragraphs)))
    contexts = {}
    for key, rule in SECTION_RULES.items():
        ranked = sorted(available, key=lambda index: _score(paragraphs[index], rule), reverse=True)
        selected = [index for index in ranked if _score(paragraphs[index], rule) > 0][:3]
        if selected:
            available.difference_update(selected)
            contexts[key] = " ".join(paragraphs[index]["original_text"] for index in selected)
        else:
            contexts[key] = ""
    # Overview gets only the case title plus isolated category signals, never a
    # copied source paragraph.
    contexts["overview"] = full_text
    return contexts


def _signals(context: str, title: str) -> dict:
    signals = extract_legal_signals(context)
    signals["title"] = title
    return signals


def _labelled(items: list[str], fallback: str) -> str:
    return ", ".join(items[:3]) if items else fallback


def _deterministic_section_bullets(key: str, context: str, title: str) -> list[str]:
    if not context:
        return list(DEFAULT_BULLETS[key])
    signal = _signals(context, title)
    articles = _labelled(signal["articles"], "no specific Article or Section extracted")
    acts = _labelled(signal["acts"], "no statute title extracted")
    dates = _labelled(signal["dates"], "no explicit date extracted")
    doctrines = _labelled(signal["doctrines"], "the legal context identified in the source")
    parties = _labelled(signal["parties"], "the parties identified in the judgment record")
    templates = {
        "facts": [f"Case background: {title or parties} concerns the factual setting identified in the record.", f"Timeline signal: {dates}.", f"Primary dispute: the source connects the dispute to {doctrines}."],
        "issues": [f"Question for determination: the court's legal inquiry concerns {articles}.", f"Statutory frame: {acts}.", f"Issue scope: the source links the question to {doctrines}."],
        "arguments": [f"Petitioner-side position: the extracted submissions concern {doctrines}.", f"Respondent-side position: the record places the response within {articles}.", "Advocacy boundary: the detailed competing submissions remain verifiable through the linked source."],
        "judgment": [f"Court determination: the decision addresses {doctrines}.", f"Legal basis considered: {articles}.", "Decision context: the operative reasoning should be read with the linked original judgment."],
        "ratio_decidendi": [f"Core legal rule: the reasoning interprets {articles}.", f"Principle applied: {doctrines}.", "Binding scope: verify the precise ratio against the linked judgment text."],
        "obiter_dicta": [f"Judicial observation: the analysis discusses {doctrines} beyond the immediate outcome.", f"Interpretive note: {acts} provides the statutory context.", "Non-binding status: verify whether an observation was necessary to the decision in the linked source."],
        "final_decision": [f"Operative outcome: the decision resolves the dispute concerning {doctrines}.", f"Disposition context: {articles} appears in the source's legal framework.", "Authoritative order: verify the final direction in the linked original judgment."],
    }
    return templates[key]


def _overview_bullets(full_text: str, title: str) -> list[str]:
    signal = _signals(full_text, title)
    return [
        f"Case synopsis: {title or 'The retrieved legal matter'} is analysed through the judgment record.",
        f"Key dates: {_labelled(signal['dates'], 'not explicitly extracted from the source')}.",
        f"Legal framework: {_labelled(signal['articles'] + signal['acts'], 'the legal instruments identified in the linked judgment')}.",
        f"Core legal themes: {_labelled(signal['doctrines'], 'the judicial reasoning reflected in the source')}.",
    ]


def _ensure_distinct(insights: dict[str, list[str]]) -> dict[str, list[str]]:
    seen = set()
    for key in INSIGHT_KEYS:
        clean = []
        for bullet in insights.get(key, []):
            normalised = _normalise(bullet).lower()
            if normalised and normalised not in seen:
                clean.append(_normalise(bullet))
                seen.add(normalised)
        if len(clean) < 2:
            for bullet in DEFAULT_BULLETS.get(key, [f"{key.replace('_', ' ').title()}: source-specific analysis is unavailable."]):
                normalised = _normalise(bullet).lower()
                if normalised not in seen:
                    clean.append(bullet)
                    seen.add(normalised)
                if len(clean) >= 2:
                    break
        insights[key] = clean[:4]
    return insights


def deterministic_insights(paragraphs: list[dict], full_text: str, title: str = "") -> dict:
    contexts = build_section_contexts(paragraphs, full_text)
    insights = {"overview": _overview_bullets(full_text, title)}
    for key in SECTION_RULES:
        insights[key] = _deterministic_section_bullets(key, contexts[key], title)
    insights = _ensure_distinct(insights)
    insights["mode"] = "deterministic-source-grounded"
    return insights


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
    source_packet = "\n\n".join(f"[{key.upper()} EVIDENCE]\n{contexts[key] or 'No isolated source passage.'}" for key in INSIGHT_KEYS)
    prompt = (
        "Return JSON only. Every required key must contain an array of 2-4 concise bullet strings, never paragraphs. "
        "Use only its matching labelled evidence. Do not reuse a source sentence, wording, or bullet across keys. "
        "Facts cover background/timeline/dispute; issues cover questions of law; arguments distinguish parties; ratio covers binding rationale; obiter covers non-binding observations; final_decision covers the operative result. "
        "When evidence is absent, provide a professional category-specific limitation bullet rather than inventing facts. "
        f"Required keys: {', '.join(INSIGHT_KEYS)}.\nCase: {title}\n\n{source_packet}"
    )
    payload = json.dumps({"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "You are a source-grounded Indian legal data scientist."}, {"role": "user", "content": prompt}]}).encode("utf-8")
    request = Request(f"{base_url}/chat/completions", data=payload, method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"])
        if not all(isinstance(data.get(key), list) and 2 <= len(data[key]) <= 4 and all(isinstance(item, str) and item.strip() for item in data[key]) for key in INSIGHT_KEYS):
            raise ValueError("LLM response did not return valid bullet arrays")
        data = _ensure_distinct(data)
        if len({_normalise(" ".join(data[key])).lower() for key in INSIGHT_KEYS}) != len(INSIGHT_KEYS):
            raise ValueError("LLM response repeated an insight block")
        data["mode"] = "llm-source-grounded"
        return data
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Legal insight LLM failed validation; using deterministic fallback: %s", exc)
        return None


def build_case_insights(title: str, paragraphs: list[dict], full_text: str) -> dict:
    contexts = build_section_contexts(paragraphs, full_text)
    return _llm_insights(title, contexts) or deterministic_insights(paragraphs, full_text, title)


def paragraph_takeaway(text: str, analysis: dict) -> dict:
    signal = extract_legal_signals(text)
    bullets = [
        f"Legal focus: {analysis.get('classification', 'Analysis')}.",
        f"Authority signal: {_labelled(signal['articles'] + signal['acts'], 'no specific authority extracted')}.",
        f"Impact marker: {_labelled(signal['doctrines'], 'review the cited source paragraph for its legal effect')}.",
    ]
    return {"bullets": bullets, "mode": "deterministic-source-grounded"}

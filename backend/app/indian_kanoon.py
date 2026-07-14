"""Small server-side adapter for the authenticated Indian Kanoon API."""
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from .analysis import analyze_paragraph, split_paragraphs
from .insights import build_case_insights, paragraph_takeaway

API_BASE = "https://api.indiankanoon.org"
PUBLIC_BASE = "https://indiankanoon.org"
logger = logging.getLogger(__name__)


class IndianKanoonError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)


def text_from_html(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()


def api_request(path: str, params: dict | None = None) -> dict:
    token = os.environ.get("INDIAN_KANOON_API_TOKEN")
    if not token:
        raise IndianKanoonError("Indian Kanoon live search is not configured. Set INDIAN_KANOON_API_TOKEN in the deployment environment.", 503)
    url = f"{API_BASE}{path}"
    if params:
        # The deployed Indian Kanoon endpoint expects a POST request while
        # retaining its search inputs in the URL query string. urlencode
        # prevents terms like "Section 302 IPC" from becoming an invalid URL.
        url = f"{url}?{urlencode(params, doseq=True, quote_via=quote_plus)}"
    request = Request(
        url,
        method="POST",
        data=b"",
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": "Legal-AI-Research-Assistant/1.0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Read the provider body once and write it to Render logs. Never pass
        # that body to the browser: it may contain provider diagnostics.
        try:
            body = exc.read().decode("utf-8", errors="replace")[:4000]
        except Exception:  # pragma: no cover - defensive logging path
            body = "<unable to read upstream response body>"
        logger.error(
            "Indian Kanoon API request failed: method=POST status=%s url=%s reason=%s body=%s",
            exc.code,
            url,
            exc.reason,
            body,
        )
        if exc.code in (401, 403):
            message = "Indian Kanoon rejected the configured API credentials. Check the server-side API token."
        elif exc.code == 405:
            message = "Indian Kanoon rejected the search request. The provider response has been logged server-side."
        else:
            message = "Indian Kanoon could not complete this request. The provider response has been logged server-side."
        raise IndianKanoonError(message, 502) from exc
    except (URLError, TimeoutError) as exc:
        raise IndianKanoonError("Indian Kanoon could not be reached. Please try again.", 503) from exc
    except json.JSONDecodeError as exc:
        raise IndianKanoonError("Indian Kanoon returned an unreadable API response.", 502) from exc


def source_url(tid: str | int, anchor: str | None = None) -> str:
    return f"{PUBLIC_BASE}/doc/{tid}/{('#' + anchor) if anchor else ''}"


def categories_to_topics(categories: list) -> list[dict]:
    topics = []
    for category in categories or []:
        for item in category[1] if len(category) > 1 else []:
            if item.get("value"):
                topics.append({"name": item["value"], "query": item.get("formInput", item["value"])})
    return topics


def search_legal_data(query: str, page: int = 0) -> dict:
    response = api_request("/search/", {"formInput": query, "pagenum": page, "maxcites": 10})
    documents = []
    for document in response.get("docs", []):
        tid = str(document.get("tid", ""))
        documents.append({"slug": tid, "name": text_from_html(document.get("title", "Untitled judgment")), "citation": text_from_html(document.get("docsource", "Indian Kanoon")), "overview": text_from_html(document.get("headline", "")), "source_url": source_url(tid), "docsize": document.get("docsize", 0)})
    topics = categories_to_topics(response.get("categories", []))
    return {"query": query, "count": response.get("found", len(documents)), "landmark_count": len(documents), "article_count": 0, "act_count": 0, "summary": f"Indian Kanoon returned {response.get('found', len(documents))} result(s) for the submitted legal query.", "results": documents, "related_topics": topics, "attribution": "Powered by Indian Kanoon"}


@lru_cache(maxsize=32)
def raw_document(tid: str) -> dict:
    return api_request(f"/doc/{tid}/", {"maxcites": 20, "maxcitedby": 20})


def html_paragraphs(tid: str, html: str) -> list[dict]:
    blocks = re.findall(r"<p\b([^>]*)>(.*?)</p>", html or "", flags=re.IGNORECASE | re.DOTALL)
    extracted = []
    for index, (attributes, content) in enumerate(blocks, start=1):
        text = text_from_html(content)
        if len(text) < 40:
            continue
        anchor_match = re.search(r"\bid=[\"']([^\"']+)", attributes, flags=re.IGNORECASE)
        extracted.append((index, text, anchor_match.group(1) if anchor_match else None))
    if not extracted:
        extracted = [(index, text, None) for index, text in enumerate(split_paragraphs(text_from_html(html)), start=1)]
    paragraphs = []
    for position, text, anchor in extracted:
        number_match = re.match(r"^\s*(?:\[|\()?([0-9]{1,4})(?:\]|\)|\.)\s*", text)
        paragraph_number = number_match.group(1) if number_match else str(position)
        analysis = analyze_paragraph(text)
        takeaway = paragraph_takeaway(text, analysis)
        paragraphs.append({"paragraph_number": paragraph_number, "classification": analysis["classification"], "original_text": text, "simplified_explanation": takeaway["bullets"][1], "ai_analysis": takeaway, "legal_terms": analysis["legal_terms"], "referenced_articles": analysis["referenced_articles"], "referenced_acts": analysis["referenced_acts"], "referenced_cases": analysis["referenced_cases"], "relevance": "This paragraph is included because it is part of the live Indian Kanoon judgment text.", "page_number": None, "citation_label": f"Paragraph {paragraph_number}; page not supplied in source HTML", "source_url": source_url(tid, anchor)})
    return paragraphs


def get_case_paragraphs(tid: str) -> list[dict]:
    document = raw_document(tid)
    return html_paragraphs(tid, document.get("doc", ""))


def case_metadata_defaults(title: str, text: str, metadata: dict, document: dict) -> tuple[str, str, str]:
    """Provide professional jurisdiction metadata for statutes and constitutional materials."""
    is_statutory_material = bool(re.search(r"\b(article|section|constitution|act|rules?)\b", title, flags=re.IGNORECASE))
    if is_statutory_material:
        enactment = re.search(r"\b(?:enacted|amended|commenced|constitution).*?\b((?:18|19|20)\d{2})\b", text, flags=re.IGNORECASE)
        first_year = enactment.group(1) if enactment else next(iter(re.findall(r"\b(?:18|19|20)\d{2}\b", text)), "Not supplied by source")
        return (
            "Supreme Court of India / Respective High Courts (Jurisdictional Scope)",
            "Full Bench / Constitutional Interpretation",
            first_year,
        )
    return (
        text_from_html(document.get("docsource", metadata.get("court", "Not supplied by source"))),
        text_from_html(str(metadata.get("bench", "Not supplied by source"))),
        str(metadata.get("year", "Not supplied by source")),
    )


def get_case(tid: str) -> dict:
    document = raw_document(tid)
    metadata = document.get("docmeta", {})
    text = text_from_html(document.get("doc", ""))
    paragraphs = html_paragraphs(tid, document.get("doc", ""))
    title = text_from_html(document.get("title", metadata.get("title", "Indian Kanoon judgment")))
    citations = document.get("citeList", [])
    insights = build_case_insights(title, paragraphs, text)
    court, bench, year = case_metadata_defaults(title, text, metadata, document)
    return {"slug": tid, "name": title, "court": court, "bench": bench, "judges": text_from_html(str(metadata.get("author", "Not supplied by source"))), "year": year, "citation": text_from_html(str(citations[0].get("title", "Indian Kanoon live judgment") if citations and isinstance(citations[0], dict) else "Indian Kanoon live judgment")), **insights, "topics": [], "source_url": source_url(tid), "attribution": "Powered by Indian Kanoon"}


def authority_items(document: dict, tid: str) -> list[dict]:
    """Normalize direct citations and citing decisions from the source payload."""
    results = []
    for field, relationship in (("citeList", "Cited authority"), ("citedbyList", "Cited by")):
        for item in document.get(field, []) or []:
            if not isinstance(item, dict):
                continue
            target = str(item.get("tid", ""))
            if not target or target == tid:
                continue
            results.append({
                "name": text_from_html(item.get("title", "Referenced judgment")),
                "slug": target,
                "similarity_score": 1.0,
                "reason": relationship,
                "source_url": source_url(target),
            })
    return results


def semantic_search_query(document: dict) -> str:
    title = text_from_html(document.get("title", ""))
    text = text_from_html(document.get("doc", ""))
    articles = re.findall(r"\bArticle\s+\d+(?:\s*\([^)]+\))*", text, flags=re.IGNORECASE)[:2]
    acts = re.findall(r"\b[A-Z][A-Za-z,&\- ]{2,60}\s+Act(?:,?\s+\d{4})?", text)[:1]
    query = " ".join((title.split()[:8] + articles + acts)).strip()
    return query or title or "Indian constitutional law"


@lru_cache(maxsize=32)
def get_case_similar(tid: str) -> list[dict]:
    document = raw_document(tid)
    results = authority_items(document, tid)
    seen = {item["slug"] for item in results}
    if len(results) < 5:
        try:
            fallback = search_legal_data(semantic_search_query(document))
            for item in fallback["results"]:
                if item["slug"] == tid or item["slug"] in seen:
                    continue
                results.append({"name": item["name"], "slug": item["slug"], "similarity_score": 0.72, "reason": "Related live search result based on title, statutes, and legal context", "source_url": item["source_url"]})
                seen.add(item["slug"])
                if len(results) >= 10:
                    break
        except IndianKanoonError as exc:
            logger.warning("Similar-case fallback search failed for %s: %s", tid, exc.message)
    return results[:10]


@lru_cache(maxsize=32)
def get_case_tree(tid: str) -> dict:
    """Build up to ten nodes across two citation generations."""
    case = get_case(tid)
    nodes = [{"name": case["name"], "slug": tid, "year": case["year"], "is_current": True, "relationship": "Selected judgment", "parent_slug": None, "depth": 0, "source_url": case["source_url"]}]
    seen = {tid}
    first_generation = authority_items(raw_document(tid), tid)[:5]
    for item in first_generation:
        if item["slug"] in seen:
            continue
        seen.add(item["slug"])
        nodes.append({**item, "relationship": item["reason"], "year": "Source date not supplied", "is_current": False, "parent_slug": tid, "depth": 1})
    for parent in list(nodes[1:])[:3]:
        if len(nodes) >= 10:
            break
        try:
            nested = authority_items(raw_document(parent["slug"]), parent["slug"])
        except IndianKanoonError as exc:
            logger.warning("Heritage expansion failed for %s: %s", parent["slug"], exc.message)
            continue
        for item in nested:
            if len(nodes) >= 10:
                break
            if item["slug"] in seen:
                continue
            seen.add(item["slug"])
            nodes.append({**item, "relationship": item["reason"], "year": "Source date not supplied", "is_current": False, "parent_slug": parent["slug"], "depth": 2})
    return {"root": {"label": "Selected live judgment", "topics": [case["name"]]}, "nodes": nodes}


def get_case_graph(tid: str) -> dict:
    case = get_case(tid)
    paragraphs = get_case_paragraphs(tid)
    values = lambda key: sorted({value for paragraph in paragraphs for value in paragraph[key]})
    return {"case": case["name"], "nodes": {"Articles": values("referenced_articles"), "Acts": values("referenced_acts"), "Sections": sorted(set(re.findall(r"\bSection\s+\d+[A-Za-z]*", " ".join(item["original_text"] for item in paragraphs), flags=re.IGNORECASE))), "Judges": [case["judges"]] if case["judges"] != "Not supplied by source" else [], "Petitioners": [], "Respondents": [], "Legal Doctrines": values("legal_terms"), "Referenced Previous Cases": values("referenced_cases"), "Similar Cases": [item["name"] for item in get_case_similar(tid)]}}

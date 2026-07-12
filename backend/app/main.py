from contextlib import asynccontextmanager
import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import connection, initialize_database
from .ingestion import backfill_document_paragraphs, ingest_pdf


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    backfill_document_paragraphs()
    yield


app = FastAPI(title="Legal AI Research API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIRECTORY = Path(os.environ.get("LEGAL_AI_UPLOAD_DIRECTORY", Path(__file__).resolve().parent.parent / "uploads"))
FRONTEND_DIRECTORY = Path(__file__).resolve().parents[2] / "frontend"


class ResearchQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    case_slug: str | None = None


def split_values(value: str) -> list[str]:
    return [entry.strip() for entry in value.split(";") if entry.strip()]


def case_payload(row):
    result = dict(row)
    with connection() as conn:
        result["topics"] = [item["name"] for item in conn.execute("""SELECT topics.name FROM topics JOIN case_topics ON case_topics.topic_id = topics.id WHERE case_topics.case_id = ? ORDER BY topics.name""", (row["id"],))]
    return result


def case_topics_by_id(conn) -> dict[int, set[str]]:
    mapping: dict[int, set[str]] = {}
    for row in conn.execute("""SELECT case_topics.case_id, topics.name FROM case_topics JOIN topics ON topics.id = case_topics.topic_id"""):
        mapping.setdefault(row["case_id"], set()).add(row["name"])
    return mapping


def legal_keywords(case: dict) -> set[str]:
    stop_words = {"about", "after", "again", "against", "because", "before", "being", "between", "court", "could", "decision", "freedom", "from", "have", "into", "issue", "judgment", "legal", "petitioner", "respondent", "should", "state", "their", "there", "these", "they", "this", "under", "whether", "which", "with"}
    text = " ".join(str(case.get(field, "")) for field in ("overview", "facts", "issues", "arguments", "judgment", "ratio_decidendi"))
    return {word.lower() for word in re.findall(r"[A-Za-z]{5,}", text) if word.lower() not in stop_words}


def dynamic_similar_cases(slug: str) -> list[dict]:
    with connection() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM cases").fetchall()]
        topics = case_topics_by_id(conn)
    source = next((row for row in rows if row["slug"] == slug), None)
    if not source:
        raise HTTPException(status_code=404, detail="Case not found")
    source_topics, source_terms = topics.get(source["id"], set()), legal_keywords(source)
    results = []
    for target in rows:
        if target["id"] == source["id"]:
            continue
        target_topics, target_terms = topics.get(target["id"], set()), legal_keywords(target)
        topic_overlap = source_topics & target_topics
        term_overlap = source_terms & target_terms
        topic_score = len(topic_overlap) / len(source_topics | target_topics) if source_topics | target_topics else 0
        term_score = len(term_overlap) / len(source_terms | target_terms) if source_terms | target_terms else 0
        score = round((topic_score * 0.7 + term_score * 0.3), 3)
        reason_parts = []
        if topic_overlap:
            reason_parts.append("Shared topics: " + ", ".join(sorted(topic_overlap)))
        if term_overlap:
            reason_parts.append("Shared legal language")
        results.append({"name": target["name"], "slug": target["slug"], "similarity_score": score, "reason": "; ".join(reason_parts) or "Related constitutional-law record"})
    return sorted(results, key=lambda item: item["similarity_score"], reverse=True)


def document_analysis(document_id: int) -> dict:
    with connection() as conn:
        document = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        pages = conn.execute("SELECT text_content FROM document_pages WHERE document_id = ? ORDER BY page_number", (document_id,)).fetchall()
        classifications = conn.execute("SELECT classification, COUNT(*) AS count FROM document_paragraphs WHERE document_id = ? GROUP BY classification ORDER BY count DESC", (document_id,)).fetchall()
    text = "\n".join(page["text_content"] for page in pages)
    checks = [("Limitation / deadline", r"\b(within|days?|months?|limitation|deadline|expire[sd]?)\b", "Review all stated dates and limitation periods."), ("Jurisdiction", r"\b(jurisdiction|court|venue|territorial)\b", "Confirm the stated court or forum has jurisdiction."), ("Financial exposure", r"\b(damages?|penalt(?:y|ies)|compensation|interest|costs?)\b", "Check amounts, triggers, and any cap or indemnity wording."), ("Termination / remedies", r"\b(terminate|termination|breach|remed(?:y|ies)|injunction)\b", "Review the breach, cure, termination, and remedy provisions.")]
    risks = [{"title": title, "mentions": len(re.findall(pattern, text, flags=re.IGNORECASE)), "recommendation": advice} for title, pattern, advice in checks if re.search(pattern, text, flags=re.IGNORECASE)]
    return {"document_id": document_id, "filename": document["original_filename"], "status": document["extraction_status"], "page_count": document["page_count"], "extracted_characters": document["extracted_characters"], "paragraph_summary": [dict(row) for row in classifications], "risk_vectors": risks, "notice": "Keyword-assisted review aid only, not legal advice. Have a qualified lawyer review the source document."}


def search_document_passages(query: str, limit: int = 10) -> list[dict]:
    words = list(dict.fromkeys(re.findall(r"[a-zA-Z0-9]{3,}", query.lower())))
    if not words:
        return []
    match_query = " OR ".join(f'"{word}"' for word in words)
    with connection() as conn:
        rows = conn.execute("""SELECT filename, page_number, text_content, bm25(document_search) AS rank
                               FROM document_search WHERE document_search MATCH ? ORDER BY rank LIMIT ?""", (match_query, limit)).fetchall()
    results = []
    for row in rows:
        text = row["text_content"]
        match = re.search(r".{0,180}(?:" + "|".join(re.escape(word) for word in words) + r").{0,300}", text, re.IGNORECASE | re.DOTALL)
        results.append({"name": row["filename"], "citation": f"Page {row['page_number']}", "source_type": "uploaded document", "excerpt": re.sub(r"\s+", " ", match.group(0) if match else text[:480]).strip()})
    return results


@app.get("/health")
def health():
    return {"status": "ok", "service": "legal-ai-api"}


@app.get("/api/topics")
def get_topics():
    with connection() as conn:
        return [row["name"] for row in conn.execute("SELECT name FROM topics ORDER BY name")]


@app.get("/api/search")
def search_cases(query: Annotated[str, Query(max_length=200)] = "", topic: str | None = None):
    term = f"%{query.strip()}%"
    sql = """SELECT DISTINCT cases.* FROM cases LEFT JOIN case_topics ON case_topics.case_id=cases.id LEFT JOIN topics ON topics.id=case_topics.topic_id WHERE (cases.name LIKE ? OR cases.overview LIKE ? OR cases.citation LIKE ? OR topics.name LIKE ?)"""
    params = [term, term, term, term]
    if topic:
        sql += " AND cases.id IN (SELECT case_id FROM case_topics JOIN topics ON topics.id=case_topics.topic_id WHERE topics.name=?)"
        params.append(topic)
    sql += " ORDER BY cases.year"
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        results = [case_payload(row) for row in rows]
        case_ids = [row["id"] for row in rows]
        paragraph_rows = conn.execute(f"SELECT referenced_articles, referenced_acts FROM paragraphs WHERE case_id IN ({','.join('?' for _ in case_ids) or 'NULL'})", case_ids).fetchall() if case_ids else []
    related_topics = sorted({topic_name for result in results for topic_name in result["topics"]})
    articles = sorted({value for row in paragraph_rows for value in split_values(row["referenced_articles"])})
    acts = sorted({value for row in paragraph_rows for value in split_values(row["referenced_acts"])})
    query_label = query.strip() or topic or "the local legal database"
    summary = f"Found {len(results)} local judgment(s) related to {query_label}, across {len(related_topics)} legal topic(s)."
    return {"query": query, "topic": topic, "count": len(results), "landmark_count": len(results), "article_count": len(articles), "act_count": len(acts), "summary": summary, "results": results, "related_topics": related_topics}


@app.get("/api/cases/{slug}")
def get_case(slug: str):
    with connection() as conn:
        row = conn.execute("SELECT * FROM cases WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_payload(row)


@app.get("/api/cases/{slug}/paragraphs")
def get_paragraphs(slug: str):
    with connection() as conn:
        rows = conn.execute("""SELECT paragraphs.* FROM paragraphs JOIN cases ON cases.id=paragraphs.case_id WHERE cases.slug=? ORDER BY paragraphs.id""", (slug,)).fetchall()
    return [{**dict(row), "legal_terms": split_values(row["legal_terms"]), "referenced_articles": split_values(row["referenced_articles"]), "referenced_acts": split_values(row["referenced_acts"]), "referenced_cases": split_values(row["referenced_cases"])} for row in rows]


@app.get("/api/cases/{slug}/similar")
def similar_cases(slug: str):
    return dynamic_similar_cases(slug)


@app.get("/api/cases/{slug}/heritage")
def heritage_tree(slug: str):
    with connection() as conn:
        source = conn.execute("SELECT * FROM cases WHERE slug = ?", (slug,)).fetchone()
        if not source:
            raise HTTPException(status_code=404, detail="Case not found")
        topics = case_topics_by_id(conn)
        rows = [dict(row) for row in conn.execute("SELECT * FROM cases ORDER BY year").fetchall()]
    source = dict(source)
    source_topics = topics.get(source["id"], set())
    related = []
    for row in rows:
        overlap = source_topics & topics.get(row["id"], set())
        if overlap:
            related.append({"name": row["name"], "slug": row["slug"], "year": row["year"], "is_current": row["id"] == source["id"], "relationship": "Shared topic: " + ", ".join(sorted(overlap))})
    return {"root": {"label": "Research topics", "topics": sorted(source_topics)}, "nodes": related}


@app.get("/api/cases/{slug}/graph")
def knowledge_graph(slug: str):
    with connection() as conn:
        case = conn.execute("SELECT * FROM cases WHERE slug = ?", (slug,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        paragraphs = conn.execute("SELECT * FROM paragraphs WHERE case_id = ?", (case["id"],)).fetchall()
    record = dict(case)
    articles = sorted({value for paragraph in paragraphs for value in split_values(paragraph["referenced_articles"])})
    acts = sorted({value for paragraph in paragraphs for value in split_values(paragraph["referenced_acts"])})
    cited_cases = sorted({value for paragraph in paragraphs for value in split_values(paragraph["referenced_cases"])})
    sections = sorted(set(re.findall(r"\bSection\s+\d+[A-Za-z]*", " ".join(paragraph["original_text"] for paragraph in paragraphs), flags=re.IGNORECASE)))
    parties = re.split(r"\s+v(?:s\.?|\.)\s+", record["name"], maxsplit=1, flags=re.IGNORECASE)
    return {"case": record["name"], "nodes": {"Articles": articles, "Acts": acts, "Sections": sections, "Judges": split_values(record["judges"]), "Petitioners": parties[:1], "Respondents": parties[1:], "Legal Doctrines": case_payload(case)["topics"], "Referenced Previous Cases": cited_cases, "Similar Cases": [item["name"] for item in dynamic_similar_cases(slug)[:4]]}}


@app.get("/api/documents")
def list_documents():
    with connection() as conn:
        rows = conn.execute("""SELECT id, original_filename, page_count, extracted_characters, extraction_status, extraction_error, ingested_at FROM documents ORDER BY id DESC""").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "upload.pdf").name
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported at present")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIRECTORY / filename
    destination.write_bytes(contents)
    result = ingest_pdf(destination)
    return {**result, "analysis": document_analysis(result["document_id"]), "paragraphs": get_document_paragraphs(result["document_id"])}


@app.get("/api/documents/{document_id}/analysis")
def get_document_analysis(document_id: int):
    return document_analysis(document_id)


@app.get("/api/documents/{document_id}/paragraphs")
def get_document_paragraphs(document_id: int):
    with connection() as conn:
        exists = conn.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Document not found")
        rows = conn.execute("SELECT * FROM document_paragraphs WHERE document_id = ? ORDER BY page_number, paragraph_number", (document_id,)).fetchall()
    return [{**dict(row), "legal_terms": split_values(row["legal_terms"]), "referenced_articles": split_values(row["referenced_articles"]), "referenced_acts": split_values(row["referenced_acts"]), "referenced_cases": split_values(row["referenced_cases"])} for row in rows]


@app.get("/api/documents/search")
def search_documents(query: Annotated[str, Query(min_length=3, max_length=200)]):
    return {"query": query, "results": search_document_passages(query)}


@app.post("/api/research/answer")
def answer_research_question(payload: ResearchQuestion):
    stop_words = {"about", "does", "from", "have", "into", "what", "when", "where", "which", "with", "would", "case", "cases", "that", "this", "they", "their", "there", "please", "tell", "said", "says"}
    words = list(dict.fromkeys(word.lower() for word in re.findall(r"[a-zA-Z]{3,}", payload.question) if word.lower() not in stop_words))
    with connection() as conn:
        rows = conn.execute("SELECT * FROM cases WHERE slug = ?", (payload.case_slug,)).fetchall() if payload.case_slug else conn.execute("SELECT * FROM cases").fetchall()
    ranked = []
    for row in rows:
        record = dict(row)
        corpus = " ".join(str(record.get(field, "")) for field in ("name", "overview", "facts", "issues", "judgment", "ratio_decidendi", "obiter_dicta")).lower()
        score = sum(word in corpus for word in words)
        if score:
            ranked.append((score, record))
    ranked.sort(key=lambda item: item[0], reverse=True)
    case_sources = [record for _, record in ranked[:3]] or ([dict(row) for row in rows] if payload.case_slug else [])
    document_sources = search_document_passages(" ".join(words), limit=3)
    if not case_sources and not document_sources:
        return {"answer": "I could not find support for that question in the local cases or uploaded text. Select a case or upload a text-based judgment PDF.", "sources": [], "notice": "Local-source answer only; not legal advice."}
    if case_sources:
        lead = case_sources[0]
        answer = f"Based on the local case record, {lead['name']} ({lead['citation']}) states: {lead['ratio_decidendi']} Its recorded outcome is: {lead['final_decision']}"
    else:
        answer = "I found relevant text in an uploaded document. The extracted passage is shown below; verify it against the original PDF before relying on it."
    sources = [{"name": item["name"], "citation": item["citation"], "source_type": "case record", "slug": item["slug"]} for item in case_sources] + document_sources
    return {"answer": answer, "sources": sources, "notice": "Answer generated from local case records and uploaded text only; verify against the primary judgment."}


# In production the FastAPI service also serves the frontend, so one public URL works on every device.
app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")

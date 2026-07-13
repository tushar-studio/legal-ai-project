"""Live Legal Research API backed by the official Indian Kanoon API."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .indian_kanoon import IndianKanoonError, get_case, get_case_graph, get_case_paragraphs, get_case_similar, get_case_tree, search_legal_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Legal AI Research API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], allow_methods=["GET", "POST"], allow_headers=["*"])

FRONTEND_DIRECTORY = Path(__file__).resolve().parents[2] / "frontend"


class ResearchQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    case_slug: str | None = None


def kanoon_or_http_error(callback):
    try:
        return callback()
    except IndianKanoonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/health")
def health():
    return {"status": "ok", "service": "legal-ai-api", "source": "Indian Kanoon API", "configured": bool(os.environ.get("INDIAN_KANOON_API_TOKEN"))}


@app.get("/api/topics")
def get_topics():
    return []


@app.get("/api/search")
def search_cases(query: Annotated[str, Query(min_length=2, max_length=200)], topic: str | None = None, page: Annotated[int, Query(ge=0)] = 0):
    search_query = topic or query
    return kanoon_or_http_error(lambda: search_legal_data(search_query, page))


@app.get("/api/cases/{slug}")
def get_case_details(slug: str):
    return kanoon_or_http_error(lambda: get_case(slug))


@app.get("/api/cases/{slug}/paragraphs")
def get_paragraphs(slug: str):
    return kanoon_or_http_error(lambda: get_case_paragraphs(slug))


@app.get("/api/cases/{slug}/similar")
def similar_cases(slug: str):
    return kanoon_or_http_error(lambda: get_case_similar(slug))


@app.get("/api/cases/{slug}/heritage")
def heritage_tree(slug: str):
    return kanoon_or_http_error(lambda: get_case_tree(slug))


@app.get("/api/cases/{slug}/graph")
def knowledge_graph(slug: str):
    return kanoon_or_http_error(lambda: get_case_graph(slug))


@app.post("/api/research/answer")
def answer_research_question(payload: ResearchQuestion):
    if not payload.case_slug:
        raise HTTPException(status_code=422, detail="Select a live judgment before requesting an analysis.")
    paragraphs = kanoon_or_http_error(lambda: get_case_paragraphs(payload.case_slug))
    words = {word.lower() for word in payload.question.split() if len(word) > 3}
    ranked = sorted(paragraphs, key=lambda paragraph: sum(word in paragraph["original_text"].lower() for word in words), reverse=True)
    sources = [paragraph for paragraph in ranked[:3] if paragraph["original_text"]]
    if not sources:
        return {"answer": "No relevant source paragraph was available for this question.", "sources": [], "notice": "The response is limited to the selected Indian Kanoon judgment."}
    answer = "The following source paragraphs are the closest matches to the research question. Review the cited original text before relying on any conclusion."
    return {"answer": answer, "sources": [{"name": f"Paragraph {item['paragraph_number']}", "citation": item["citation_label"], "source_url": item["source_url"], "excerpt": item["original_text"]} for item in sources], "notice": "Source: Indian Kanoon. Page numbers are shown only when supplied by the source document."}


app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")

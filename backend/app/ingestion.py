import hashlib
from pathlib import Path

from pypdf import PdfReader

from .analysis import analyze_paragraph, split_paragraphs
from .database import connection


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def store_paragraphs(conn, document_id: int, pages: list[tuple[int, str]]) -> None:
    paragraphs = []
    for page_number, page_text in pages:
        for paragraph_number, paragraph_text in enumerate(split_paragraphs(page_text), start=1):
            analysis = analyze_paragraph(paragraph_text)
            paragraphs.append((document_id, page_number, paragraph_number, analysis["classification"], paragraph_text, "; ".join(analysis["legal_terms"]), "; ".join(analysis["referenced_articles"]), "; ".join(analysis["referenced_acts"]), "; ".join(analysis["referenced_cases"])))
    if paragraphs:
        conn.executemany("""INSERT OR IGNORE INTO document_paragraphs(document_id, page_number, paragraph_number, classification, original_text, legal_terms, referenced_articles, referenced_acts, referenced_cases)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", paragraphs)


def backfill_document_paragraphs() -> None:
    with connection() as conn:
        documents = conn.execute("SELECT id FROM documents WHERE NOT EXISTS (SELECT 1 FROM document_paragraphs WHERE document_paragraphs.document_id = documents.id)").fetchall()
        for document in documents:
            pages = [(row["page_number"], row["text_content"]) for row in conn.execute("SELECT page_number, text_content FROM document_pages WHERE document_id = ? ORDER BY page_number", (document["id"],))]
            store_paragraphs(conn, document["id"], pages)


def ingest_pdf(path: Path) -> dict:
    path = path.resolve()
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")
    if not path.is_file():
        raise FileNotFoundError(path)

    checksum = sha256_of(path)
    with connection() as conn:
        existing = conn.execute("SELECT id, original_filename, extraction_status FROM documents WHERE sha256 = ?", (checksum,)).fetchone()
        if existing:
            return {"status": "duplicate", "document_id": existing["id"], "filename": existing["original_filename"], "extraction_status": existing["extraction_status"]}

    try:
        reader = PdfReader(str(path), strict=False)
        pages = [(number, reader.pages[number - 1].extract_text() or "") for number in range(1, len(reader.pages) + 1)]
        character_count = sum(len(text) for _, text in pages)
        status = "text_extracted" if character_count else "ocr_required"
        error = None
    except Exception as exc:
        pages, character_count, status, error = [], 0, "failed", str(exc)

    with connection() as conn:
        cursor = conn.execute(
            """INSERT INTO documents(original_filename, source_path, sha256, page_count, extracted_characters, extraction_status, extraction_error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (path.name, str(path), checksum, len(pages), character_count, status, error),
        )
        document_id = cursor.lastrowid
        if pages:
            conn.executemany("INSERT INTO document_pages(document_id, page_number, text_content) VALUES (?, ?, ?)", [(document_id, number, text) for number, text in pages])
            conn.executemany("INSERT INTO document_search(document_id, page_number, filename, text_content) VALUES (?, ?, ?, ?)", [(document_id, number, path.name, text) for number, text in pages])
            store_paragraphs(conn, document_id, pages)
    return {"status": status, "document_id": document_id, "filename": path.name, "page_count": len(pages), "extracted_characters": character_count, "error": error}

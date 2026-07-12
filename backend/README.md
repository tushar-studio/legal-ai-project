# Legal AI Backend

FastAPI and SQLite foundation for the Legal AI Research Assistant.

## Run locally

```powershell
cd E:\legal-ai-project\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to try the API. The SQLite database is created and seeded automatically on first run.

## Working local features

- Search and inspect the seeded constitutional-law cases.
- Upload a text-based PDF from the frontend; text is extracted and recorded in SQLite.
- During ingestion, extracted text is split into paragraphs and given deterministic classifications, legal terms, article references, Act references, and case-reference metadata. View this data at `GET /api/documents/{document_id}/paragraphs`.
- Search extracted PDF passages with `GET /api/documents/search?query=...`; uploaded pages are indexed locally with SQLite full-text search.
- Similar-case scores and the heritage tree are generated from the stored case topics and legal-language overlap through `/api/cases/{slug}/similar` and `/api/cases/{slug}/heritage`.
- Review transparent keyword-based risk vectors for uploaded documents.
- Ask a research question in the chat panel; answers cite local case records and relevant passages from extracted uploaded PDFs.

The current analyzer and chat are local review aids, not legal advice or a substitute for verifying the primary judgment. Scanned PDFs need OCR support before their text can be analyzed.

## Verify the core workflow

```powershell
cd E:\legal-ai-project\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Deploy publicly (Render)

This repository includes `render.yaml`, which deploys one FastAPI web service that also serves the frontend. This gives the application one public URL that works on phones and laptops.

1. Create a GitHub repository and push this project to it.
2. In Render, choose **New → Blueprint**, connect that repository, and approve the detected `render.yaml`.
3. Render will provide an `onrender.com` URL. Share that URL to open the app from any device.

The blueprint keeps the SQLite database and uploaded PDFs on `/var/data`, a persistent disk. A Render persistent disk requires a paid web-service plan. For a custom domain, add it in the Render service settings after the first deploy.

# Legal AI Backend

FastAPI service for the live Indian Kanoon-backed Legal AI Research Assistant.

## Run locally

```powershell
cd E:\legal-ai-project\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Set `INDIAN_KANOON_API_TOKEN` before starting the service. The token stays server-side and must never be placed in frontend JavaScript.

For local development, copy `.env.example` values into your shell environment before running Uvicorn.

## Live data flow

- `GET /api/search?query=...` requests live Indian Kanoon search results.
- `GET /api/cases/{id}` and the related paragraph, citation tree, similar-case, and graph routes retrieve the selected live judgment.
- Every displayed analysis section links back to the original Indian Kanoon judgment source. When the source HTML does not expose a page number, the interface explicitly says so rather than inventing one.

Indian Kanoon API attribution is displayed in the application. Review Indian Kanoon's API documentation and terms before deploying.

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

During the first Render Blueprint setup, enter `INDIAN_KANOON_API_TOKEN` when Render prompts for it. For a custom domain, add it in the Render service settings after the first deploy.

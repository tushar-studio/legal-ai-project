"""Ingest a directory of text-based judgment PDFs into the local SQLite database."""
import argparse
from pathlib import Path

from app.database import initialize_database
from app.ingestion import ingest_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_directory", type=Path, help="Folder containing PDFs")
    args = parser.parse_args()
    initialize_database()
    files = sorted(args.source_directory.glob("*.pdf"))
    if not files:
        raise SystemExit("No PDF files found.")
    for path in files:
        result = ingest_pdf(path)
        print(f"{result['filename']}: {result['status']} ({result.get('page_count', 0)} pages, {result.get('extracted_characters', 0)} characters)")


if __name__ == "__main__":
    main()

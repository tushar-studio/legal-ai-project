import os
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(os.environ.get("LEGAL_AI_DATABASE_PATH", Path(__file__).resolve().parent.parent / "legal_ai.db"))


def connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                court TEXT NOT NULL,
                bench TEXT,
                judges TEXT,
                year INTEGER NOT NULL,
                citation TEXT NOT NULL,
                overview TEXT NOT NULL,
                facts TEXT NOT NULL,
                issues TEXT NOT NULL,
                arguments TEXT NOT NULL,
                judgment TEXT NOT NULL,
                ratio_decidendi TEXT NOT NULL,
                obiter_dicta TEXT NOT NULL,
                final_decision TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS case_topics (
                case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                PRIMARY KEY (case_id, topic_id)
            );

            CREATE TABLE IF NOT EXISTS paragraphs (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                paragraph_number TEXT NOT NULL,
                classification TEXT NOT NULL,
                original_text TEXT NOT NULL,
                simplified_explanation TEXT NOT NULL,
                legal_terms TEXT NOT NULL DEFAULT '',
                referenced_articles TEXT NOT NULL DEFAULT '',
                referenced_acts TEXT NOT NULL DEFAULT '',
                referenced_cases TEXT NOT NULL DEFAULT '',
                relevance TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS case_relations (
                source_case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                target_case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL,
                similarity_score REAL,
                PRIMARY KEY (source_case_id, target_case_id, relation_type)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                original_filename TEXT NOT NULL,
                source_path TEXT NOT NULL,
                sha256 TEXT NOT NULL UNIQUE,
                page_count INTEGER NOT NULL DEFAULT 0,
                extracted_characters INTEGER NOT NULL DEFAULT 0,
                extraction_status TEXT NOT NULL,
                extraction_error TEXT,
                ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS document_pages (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                text_content TEXT NOT NULL DEFAULT '',
                UNIQUE(document_id, page_number)
            );

            CREATE TABLE IF NOT EXISTS document_paragraphs (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                paragraph_number INTEGER NOT NULL,
                classification TEXT NOT NULL,
                original_text TEXT NOT NULL,
                legal_terms TEXT NOT NULL DEFAULT '',
                referenced_articles TEXT NOT NULL DEFAULT '',
                referenced_acts TEXT NOT NULL DEFAULT '',
                referenced_cases TEXT NOT NULL DEFAULT '',
                UNIQUE(document_id, page_number, paragraph_number)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5(
                document_id UNINDEXED,
                page_number UNINDEXED,
                filename UNINDEXED,
                text_content
            );

            """
        )
        conn.execute(
            """INSERT INTO document_search(document_id, page_number, filename, text_content)
               SELECT document_pages.document_id, document_pages.page_number, documents.original_filename, document_pages.text_content
               FROM document_pages JOIN documents ON documents.id = document_pages.document_id
               WHERE NOT EXISTS (SELECT 1 FROM document_search WHERE document_search.document_id = document_pages.document_id AND document_search.page_number = document_pages.page_number)"""
        )
        if conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 0:
            seed_database(conn)


def seed_database(conn: sqlite3.Connection) -> None:
    cases = [
        ("romesh-thappar", "Romesh Thappar v. State of Madras", 1950, "1950 AIR 124", "5 Judges", "Supreme Court of India", "Supreme Court of India", "A foundational decision holding that freedom of speech includes freedom of circulation.", "The Madras Government prohibited the entry and circulation of the weekly journal Cross Roads.", "Whether the prohibition violated Article 19(1)(a) and was protected by Article 19(2).", "The petitioner challenged the circulation ban as unconstitutional.", "The Court struck down the order.", "Freedom of speech includes propagation of ideas and freedom of circulation.", "Speech restrictions must fall strictly within constitutional exceptions.", "Petition allowed; prohibition order invalidated."),
        ("brij-bhushan", "Brij Bhushan v. State of Delhi", 1950, "1950 AIR 129", "5 Judges", "Supreme Court of India", "Supreme Court of India", "A leading decision against prior censorship of the press.", "The publisher of Organizer was directed to submit material for scrutiny before publication.", "Whether pre-censorship violated Article 19(1)(a).", "The order imposed unconstitutional prior restraint.", "The Court invalidated the pre-censorship order.", "Prior restraint is a serious restriction on press freedom.", "Any restraint must satisfy Article 19(2).", "Order struck down."),
        ("bennett-coleman", "Bennett Coleman v. Union of India", 1972, "1973 SCR (2) 757", "5 Judges", "Supreme Court of India", "Supreme Court of India", "Newsprint controls could not indirectly restrict the reach of newspapers.", "Newsprint policy limited newspaper page capacity.", "Whether economic regulation directly affected free speech.", "Page limits reduced circulation and expression.", "The policy was held unconstitutional in relevant respects.", "Direct impact on speech matters even for economic laws.", "Press freedom protects circulation and content choices.", "Petition allowed."),
        ("indian-express", "Indian Express Newspapers v. Union of India", 1985, "1985 SCC (1) 641", "2 Judges", "Supreme Court of India", "Supreme Court of India", "Taxes on newsprint cannot become a tool to suppress the press.", "Import duty on newsprint increased publication costs.", "Whether the fiscal burden impaired press freedom.", "The levy threatened circulation and access to information.", "The Court required special care when taxation affects the press.", "Taxes must not stifle free expression.", "The press has a vital democratic role.", "Directions issued for reconsideration."),
        ("shreya-singhal", "Shreya Singhal v. Union of India", 2015, "(2015) 5 SCC 1", "2 Judges", "Supreme Court of India", "Supreme Court of India", "Section 66A was struck down for vagueness and overbreadth.", "Arrests were made over online comments under Section 66A.", "Whether vague online speech restrictions create a chilling effect.", "The provision lacked clear standards and enabled arbitrary enforcement.", "Section 66A was struck down.", "Vague and overbroad restrictions chill protected speech.", "Discussion, advocacy and incitement require different treatment.", "Section 66A invalidated."),
    ]
    conn.executemany("""INSERT INTO cases (slug,name,year,citation,bench,court,judges,overview,facts,issues,arguments,judgment,ratio_decidendi,obiter_dicta,final_decision) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", cases)
    topics = ["Press Freedom", "Constitutional Rights", "Prior Restraint", "Sedition", "Media Regulation", "Freedom of Speech", "Reasonable Restrictions"]
    conn.executemany("INSERT INTO topics(name) VALUES (?)", [(topic,) for topic in topics])
    topic_rows = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM topics")}
    case_rows = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM cases")}
    mapping = {"romesh-thappar": ["Press Freedom", "Freedom of Speech", "Reasonable Restrictions"], "brij-bhushan": ["Press Freedom", "Prior Restraint", "Freedom of Speech"], "bennett-coleman": ["Press Freedom", "Media Regulation", "Freedom of Speech"], "indian-express": ["Press Freedom", "Media Regulation", "Reasonable Restrictions"], "shreya-singhal": ["Freedom of Speech", "Media Regulation", "Reasonable Restrictions"]}
    conn.executemany("INSERT INTO case_topics(case_id,topic_id) VALUES (?,?)", [(case_rows[slug], topic_rows[topic]) for slug, names in mapping.items() for topic in names])
    conn.executemany("""INSERT INTO paragraphs(case_id,paragraph_number,classification,original_text,simplified_explanation,legal_terms,referenced_articles,referenced_acts,referenced_cases,relevance) VALUES (?,?,?,?,?,?,?,?,?,?)""", [
        (case_rows["romesh-thappar"], "Paragraph 8", "Facts", "The petitioner is the printer, publisher and editor of a weekly journal called Cross Roads. The Madras Government issued an order imposing a total ban on its circulation inside the State.", "The State completely stopped this magazine from being distributed in Madras.", "Circulation; Executive order", "Article 19(1)(a)", "Madras Maintenance of Public Order Act, 1949", "", "It establishes the factual basis for testing the restriction on free speech."),
        (case_rows["romesh-thappar"], "Paragraph 14", "Freedom of Speech", "Freedom of speech and expression includes freedom of propagation of ideas, and that freedom is ensured by the freedom of circulation.", "Ideas are useful only when people can receive them; therefore, circulation is part of free speech.", "Freedom of circulation; Propagation of ideas", "Article 19(1)(a)", "", "", "This is the core legal principle of the case."),
        (case_rows["romesh-thappar"], "Paragraph 20", "Public Order", "A law restricting expression can survive only when the restriction is authorised by the constitutional grounds then available under Article 19(2).", "The government cannot limit speech for reasons that the Constitution does not permit.", "Reasonable restriction; Public order", "Article 19(2)", "Madras Maintenance of Public Order Act, 1949", "", "It explains why the impugned law could not justify the circulation ban."),
    ])
    relations = [("romesh-thappar", "brij-bhushan", 0.92), ("romesh-thappar", "bennett-coleman", 0.89), ("romesh-thappar", "indian-express", 0.85), ("romesh-thappar", "shreya-singhal", 0.82), ("bennett-coleman", "indian-express", 0.91)]
    conn.executemany("INSERT INTO case_relations(source_case_id,target_case_id,relation_type,similarity_score) VALUES (?,?, 'similar', ?)", [(case_rows[source], case_rows[target], score) for source, target, score in relations])

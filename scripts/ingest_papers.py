#!/usr/bin/env python3
"""
Populate the papers table (new schema) from parsed Docling JSON in data/parsed.

For each parsed paper we extract, best-effort:
  - title            (real paper title from the doc, fallback to filename)
  - authors text[]   (author line under the title, cleaned of affiliations/marks)
  - abstract         (text under the ABSTRACT header)
  - original_filename / storage_uri (the source PDF)
  - source_type='curated', status='completed', chunk_count (from data/chunks)

Idempotent: clears existing curated rows, then re-inserts.
Run:  .venv/bin/python scripts/ingest_papers.py [--dry-run]
"""
import os
import re
import sys
import json
import glob
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DB_URL", "postgres://nexus:PinkFloyd@localhost:5434/nexus_db?sslmode=disable")
PARSED_DIR = os.getenv("LOCAL_PARSED_DIR", "data/parsed")
RAW_DIR = os.getenv("LOCAL_RAW_PDFS_DIR", "data/raw_pdfs")
CHUNKS_DIR = os.getenv("LOCAL_CHUNKS_DIR", "data/chunks")

# Section headers that are NOT titles.
GENERIC_HEADERS = {
    "abstract", "introduction", "categories and subject descriptors",
    "general terms", "keywords", "acknowledgements", "acknowledgments",
    "references", "contents", "1. introduction",
}
# Tokens that mark a line as affiliation, not an author name.
AFFIL_MARKERS = re.compile(
    r"@|university|univ\.|institute|department|dept\.|laborator|labs?\b|inc\.?|corp|"
    r"research|college|\.com|\.edu|google|amazon|facebook|yahoo|microsoft|ibm|"
    r"school|systems|technolog|academy|gmbh|ltd", re.I)
FOOTNOTE_MARKS = re.compile(r"[\d\*∗†‡§¶†-‰\{\}\[\]<>\+#\^~]")


def clean_name(s: str) -> str:
    s = FOOTNOTE_MARKS.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" .,-")
    return s


def split_authors(line: str):
    line = line.replace(" & ", ", ").replace("\n", ", ")
    parts = re.split(r",|\band\b", line)
    out = []
    for p in parts:
        n = clean_name(p)
        if 2 < len(n) < 40 and " " in n and not AFFIL_MARKERS.search(n):
            out.append(n)
    # de-dup, preserve order
    seen, uniq = set(), []
    for n in out:
        if n.lower() not in seen:
            seen.add(n.lower()); uniq.append(n)
    return uniq


def first_real_header(texts, start):
    for i in range(start, len(texts)):
        t = texts[i]
        if t.get("label") == "section_header":
            txt = (t.get("text") or "").strip()
            if txt:
                return i, txt
    return None, None


def extract(path):
    d = json.load(open(path))
    texts = d.get("texts", [])
    base = os.path.basename(path).replace(".json", "")

    # --- title ---
    title, title_idx = None, -1
    for i, t in enumerate(texts):
        if t.get("label") in ("title", "section_header"):
            txt = (t.get("text") or "").strip()
            if txt and txt.lower() not in GENERIC_HEADERS and len(txt) > 6:
                title, title_idx = txt, i
                break
    # fall back to the filename (the canonical "paper name") when the extracted
    # title looks like a section header rather than a real title.
    if (not title
            or title.lower() in GENERIC_HEADERS
            or re.match(r"^\d+[\.\s]", title)          # "1 Introduction"
            or title.lower().rstrip(":").strip() in ("review", "abstract")
            or len(title) < 8):
        title = base.replace("_", " ").strip()

    # --- author line: text items between title and next section header ---
    nxt_idx, _ = first_real_header(texts, title_idx + 1)
    end = nxt_idx if nxt_idx else min(len(texts), title_idx + 6)
    author_line = ""
    for i in range(title_idx + 1, end):
        if texts[i].get("label") == "text":
            txt = (texts[i].get("text") or "").strip()
            if txt:
                author_line = txt
                break
    authors = split_authors(author_line) if author_line and len(author_line) < 500 else []

    # --- abstract: text after an ABSTRACT header ---
    abstract = None
    for i, t in enumerate(texts):
        if t.get("label") == "section_header" and (t.get("text") or "").strip().lower().startswith("abstract"):
            for j in range(i + 1, len(texts)):
                if texts[j].get("label") == "text" and (texts[j].get("text") or "").strip():
                    abstract = re.sub(r"\s+", " ", texts[j]["text"].strip())
                    break
            break

    # chunk count
    chunk_count = 0
    cf = os.path.join(CHUNKS_DIR, base + "_chunks.json")
    if os.path.exists(cf):
        try:
            cd = json.load(open(cf))
            chunk_count = len(cd) if isinstance(cd, list) else len(cd.get("chunks", []))
        except Exception:
            pass

    pdf = base + ".pdf"
    return {
        "title": title[:500],
        "authors": authors,
        "abstract": abstract,
        "original_filename": pdf,
        "storage_uri": os.path.join(RAW_DIR, pdf),
        "chunk_count": chunk_count,
    }


def main():
    dry = "--dry-run" in sys.argv
    rows = [extract(f) for f in sorted(glob.glob(os.path.join(PARSED_DIR, "*.json")))]

    print(f"Extracted {len(rows)} papers from {PARSED_DIR}\n")
    for r in rows:
        print(f"- {r['title'][:70]:<70} | authors={len(r['authors'])} | chunks={r['chunk_count']}")
        if r["authors"]:
            print(f"    {', '.join(r['authors'])}")
    if dry:
        print("\n[dry-run] nothing written.")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("DELETE FROM papers WHERE source_type = 'curated'")
    execute_values(cur, """
        INSERT INTO papers
            (title, authors, abstract, original_filename, storage_uri,
             source_type, visibility, status, ingested_at, chunk_count)
        VALUES %s
    """, [(
        r["title"], r["authors"], r["abstract"], r["original_filename"],
        r["storage_uri"], "curated", "public", "completed", "now()", r["chunk_count"],
    ) for r in rows], template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    conn.commit()
    print(f"\nInserted {cur.rowcount} curated papers.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

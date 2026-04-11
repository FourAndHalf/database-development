#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

import requests


OPENALEX_URL = "https://api.openalex.org/works"
EXISTING_URLS = {
    "https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf",
    "https://research.google.com/archive/bigtable-osdi06.pdf",
    "https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}

MANUAL_LINKS_RAW = {
    "Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service": "https://www.usenix.org/system/files/atc22-elhemali.pdf",
    "PNUTS: Yahoo!’s Hosted Data Serving Platform": "https://www.vldb.org/pvldb/vol1/1454167.pdf",
    "Megastore: Scalable, Highly Available Storage for Interactive Services": "https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper32.pdf",
    "Cassandra – A Decentralized Structured Storage System": "https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf",
    "Spanner: Google’s Globally-Distributed Database": "https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf",
    "F1: A Distributed SQL Database That Scales": "https://www.vldb.org/pvldb/vol6/p1068-shute.pdf",
    "Raft: In Search of an Understandable Consensus Algorithm": "https://www.usenix.org/system/files/conference/atc14/atc14-paper-ongaro.pdf",
    "ZooKeeper: Wait-free Coordination for Internet-scale Systems": "https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf",
    "The Chubby Lock Service": "https://research.google.com/archive/chubby-osdi06.pdf",
    "Chain Replication for Supporting High Throughput and Availability": "https://www.usenix.org/legacy/event/osdi04/tech/full_papers/renesse/renesse.pdf",
    "Paxos Made Simple": "https://lamport.azurewebsites.net/pubs/paxos-simple.pdf",
    "Viewstamped Replication Revisited": "https://pmg.csail.mit.edu/papers/vr-revisited.pdf",
    "Dremel: Interactive Analysis of Web-Scale Datasets": "https://www.vldb.org/pvldb/vol3/R29.pdf",
    "RocksDB: Evolution of Development Priorities in a Key-Value Store": "https://www.usenix.org/system/files/fast21-dong.pdf",
    "Consistent Hashing": "https://www.cs.princeton.edu/courses/archive/fall09/cos518/papers/chash.pdf",
}


@dataclass(frozen=True)
class Citation:
    title: str
    year: int | None
    raw_line: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_input_path() -> Path:
    plural = project_root() / "temp" / "research-papers.md"
    singular = project_root() / "temp" / "research-paper.md"
    return plural if plural.exists() else singular


def default_output_path() -> Path:
    return project_root() / "temp" / "research-paper-links.md"


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


MANUAL_LINKS = {normalize_title(k): v for k, v in MANUAL_LINKS_RAW.items()}


def clean_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^[\"'“”‘’]+|[\"'“”‘’]+$", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def extract_year(text: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        return int(match.group(0))
    return None


def extract_title_from_line(line: str) -> str | None:
    # 1) Curly-quoted paper names in bold or italics.
    for pattern in [
        r"\*\*“([^”]+)”\*\*",
        r"\*“([^”]+)”\*",
        r"“([^”]+)”",
    ]:
        match = re.search(pattern, line)
        if match:
            return clean_title(match.group(1))

    # 2) First bold segment.
    match = re.search(r"^\s*-\s+\*\*([^*]+)\*\*", line)
    if match:
        title = match.group(1)
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
        return clean_title(title)

    return None


def iter_citations(markdown_text: str) -> Iterable[Citation]:
    seen: set[str] = set()
    for line in markdown_text.splitlines():
        if not line.strip().startswith("-"):
            continue
        title = extract_title_from_line(line)
        if not title:
            continue
        norm = normalize_title(title)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        yield Citation(title=title, year=extract_year(line), raw_line=line.strip())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def informative_tokens(text: str) -> set[str]:
    return {tok for tok in normalize_title(text).split() if len(tok) > 2 and tok not in STOPWORDS}


def token_overlap(query: str, candidate: str) -> float:
    q_tokens = informative_tokens(query)
    c_tokens = informative_tokens(candidate)
    if not q_tokens:
        return 0.0
    return len(q_tokens & c_tokens) / len(q_tokens)


def as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def pick_download_urls(work: dict) -> list[str]:
    best_oa = as_dict(work.get("best_oa_location"))
    primary = as_dict(work.get("primary_location"))
    open_access = as_dict(work.get("open_access"))
    ids = as_dict(work.get("ids"))

    candidates = [
        best_oa.get("pdf_url"),
        primary.get("pdf_url"),
        open_access.get("oa_url"),
        best_oa.get("landing_page_url"),
        primary.get("landing_page_url"),
        ids.get("doi"),
    ]
    out: list[str] = []
    for url in candidates:
        if isinstance(url, str) and url.startswith("http") and url not in out:
            out.append(url)
    return out


def looks_like_pdf_url(url: str) -> bool:
    lowered = url.lower()
    if lowered.endswith(".pdf"):
        return True
    if "/pdf/" in lowered:
        return True
    if "usenix.org/system/files" in lowered:
        return True
    if "vldb.org/pvldb/" in lowered:
        return True
    return False


def verify_downloadable_pdf(session: requests.Session, url: str, timeout: int = 20) -> str | None:
    try:
        head = session.head(url, allow_redirects=True, timeout=timeout)
        final_url = head.url
        content_type = head.headers.get("content-type", "").lower()
        if head.status_code < 400 and "application/pdf" in content_type:
            return final_url
    except requests.RequestException:
        pass

    try:
        get = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
        final_url = get.url
        content_type = get.headers.get("content-type", "").lower()
        ok = get.status_code < 400 and (
            "application/pdf" in content_type or final_url.lower().endswith(".pdf")
        )
        get.close()
        return final_url if ok else None
    except requests.RequestException:
        return None


def fetch_openalex_results(session: requests.Session, params: dict) -> list[dict]:
    response = session.get(OPENALEX_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    results = data.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return []


def query_openalex(session: requests.Session, citation: Citation) -> dict | None:
    if len(informative_tokens(citation.title)) < 2:
        return None

    query_params = [
        {
            "filter": f"title.search:{citation.title}",
            "per-page": 10,
            "mailto": "research-bot@example.com",
        },
        {
            "search": citation.title,
            "per-page": 10,
            "mailto": "research-bot@example.com",
        },
    ]

    merged: list[dict] = []
    seen_ids: set[str] = set()
    for params in query_params:
        try:
            results = fetch_openalex_results(session, params)
        except requests.RequestException:
            continue
        for item in results:
            item_id = item.get("id")
            if isinstance(item_id, str) and item_id in seen_ids:
                continue
            if isinstance(item_id, str):
                seen_ids.add(item_id)
            merged.append(item)

    if not merged:
        return None

    best_work = None
    best_score = 0.0
    for work in merged:
        display_name = str(work.get("display_name", ""))
        sim = similarity(citation.title, display_name)
        overlap = token_overlap(citation.title, display_name)
        score = sim + (0.25 * overlap)

        nq = normalize_title(citation.title)
        nd = normalize_title(display_name)
        if nq and nd and (nq in nd or nd in nq):
            score += 0.1

        pub_year = work.get("publication_year")
        if citation.year and isinstance(pub_year, int):
            if citation.year == pub_year:
                score += 0.1
            elif abs(citation.year - pub_year) <= 1:
                score += 0.05

        if as_dict(work.get("open_access")).get("is_oa"):
            score += 0.05

        if pick_download_urls(work):
            score += 0.05

        year_aligned = False
        if citation.year and isinstance(pub_year, int):
            year_aligned = abs(citation.year - pub_year) <= 1

        # Precision-first quality gate.
        if not (sim >= 0.8 or (sim >= 0.72 and overlap >= 0.65 and year_aligned)):
            continue
        if overlap < 0.5:
            continue

        if score > best_score:
            best_score = score
            best_work = work

    if not best_work or best_score < 0.8:
        return None

    verified_url = None
    for candidate_url in pick_download_urls(best_work):
        if not looks_like_pdf_url(candidate_url):
            continue
        verified_url = verify_downloadable_pdf(session, candidate_url)
        if verified_url:
            break

    if not verified_url:
        return None

    return {
        "query_title": citation.title,
        "query_year": citation.year,
        "matched_title": best_work.get("display_name"),
        "matched_year": best_work.get("publication_year"),
        "score": round(best_score, 3),
        "openalex_id": best_work.get("id"),
        "download_url": verified_url,
    }


def to_markdown(found: list[dict], unresolved: list[Citation]) -> str:
    lines = []
    lines.append("# Research Paper Download Links")
    lines.append("")
    lines.append("Generated from citations in `temp/research-papers.md` via OpenAlex lookup.")
    lines.append("")
    lines.append("## Resolved")
    lines.append("")
    lines.append("| # | Query Title | Matched Title | Year | Score | Download Link |")
    lines.append("|---|---|---|---:|---:|---|")
    for idx, item in enumerate(found, start=1):
        lines.append(
            f"| {idx} | {item['query_title']} | {item['matched_title']} | "
            f"{item.get('matched_year') or ''} | {item['score']} | {item['download_url']} |"
        )

    lines.append("")
    lines.append("## Unresolved")
    lines.append("")
    if not unresolved:
        lines.append("None")
    else:
        for citation in unresolved:
            year = citation.year if citation.year else "n/a"
            lines.append(f"- {citation.title} ({year})")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve citation titles to download links.")
    parser.add_argument("--input", type=Path, default=default_input_path())
    parser.add_argument("--output", type=Path, default=default_output_path())
    parser.add_argument(
        "--json-output",
        type=Path,
        default=project_root() / "temp" / "research-paper-links.json",
    )
    parser.add_argument("--delay", type=float, default=0.2)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input file not found: {args.input}")
        return 1

    markdown_text = args.input.read_text(encoding="utf-8")
    citations = list(iter_citations(markdown_text))
    if not citations:
        print("No citations extracted.")
        return 1

    session = requests.Session()
    found: list[dict] = []
    unresolved: list[Citation] = []

    for citation in citations:
        manual_link = MANUAL_LINKS.get(normalize_title(citation.title))
        if manual_link:
            verified_manual = verify_downloadable_pdf(session, manual_link)
            if verified_manual and verified_manual not in EXISTING_URLS:
                found.append(
                    {
                        "query_title": citation.title,
                        "query_year": citation.year,
                        "matched_title": citation.title,
                        "matched_year": citation.year,
                        "score": 1.0,
                        "openalex_id": "manual",
                        "download_url": verified_manual,
                    }
                )
                print(f"[FOUND] {citation.title} -> {verified_manual} (manual)")
                time.sleep(args.delay)
                continue

        try:
            result = query_openalex(session, citation)
        except requests.RequestException:
            result = None

        if result and result["download_url"] not in EXISTING_URLS:
            found.append(result)
            print(f"[FOUND] {citation.title} -> {result['download_url']}")
        else:
            unresolved.append(citation)
            print(f"[MISS] {citation.title}")
        time.sleep(args.delay)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(to_markdown(found, unresolved), encoding="utf-8")
    args.json_output.write_text(
        json.dumps({"resolved": found, "unresolved": [c.__dict__ for c in unresolved]}, indent=2),
        encoding="utf-8",
    )

    print(
        f"\nDone. Resolved {len(found)} / {len(citations)} citations. "
        f"Markdown: {args.output} | JSON: {args.json_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

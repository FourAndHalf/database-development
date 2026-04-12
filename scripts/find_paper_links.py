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
    "Dynamo: Amazon’s Highly Available Key-Value Store": "https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf",
    "Bigtable: A Distributed Storage System for Structured Data": "https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf",
    "Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service": "https://www.usenix.org/system/files/atc22-elhemali.pdf",
    "Riak: A Distributed, Eventually-Consistent Key/Value Data Store": "https://docs.riak.com/riak/kv/latest/learn/dynamo/index.html",
    "Spanner Sans Spanner: Bigtable with Global Consistency and Coordination": "https://hal.science/tel-01956321v2/document",
    "HBase: The Hadoop Database": "https://hbase.apache.org/book.html",
    "Dynamo and Bigtable – Review and Comparison": "https://doi.org/10.1109/eeei.2014.7005771",
    "Fauna: Replicated Databases Without Strict Serializability": "https://scholar.google.com/scholar?q=Fauna%3A+Replicated+Databases+Without+Strict+Serializability",
    "Comprehensive comparison of NoSQL Databases": "https://link.springer.com/content/pdf/bfm%3A978-3-031-27908-9/1?pdf=chapter%20toc",
    "PNUTS: Yahoo!’s Hosted Data Serving Platform": "https://www.vldb.org/pvldb/vol1/1454167.pdf",
    "Megastore: Scalable, Highly Available Storage for Interactive Services": "https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper32.pdf",
    "Cassandra – A Decentralized Structured Storage System": "https://www.cs.cornell.edu/projects/ladis2009/papers/lakshman-ladis2009.pdf",
    "Spanner: Google’s Globally-Distributed Database": "https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf",
    "F1: A Distributed SQL Database That Scales": "https://www.vldb.org/pvldb/vol6/p1068-shute.pdf",
    "CockroachDB: The Resilient Geo-Distributed SQL Database": "https://dl.acm.org/doi/pdf/10.1145/3318464.3386134",
    "NewSQL: An Introduction": "https://doi.org/10.1145/1721654.1721659",
    "Tsurgeon & HydraBase": "https://scholar.google.com/scholar?q=Tsurgeon+HydraBase+transactional+layer",
    "Omega: Flexible, Scalable Multi-Database Concurrency Control": "https://storage.googleapis.com/gweb-research2023-media/pubtools/3295.pdf",
    "FLORIDA: FRATernal Lock-Free Replication for Geo-Distributed Transactions": "https://scholar.google.com/scholar?q=FLORIDA+FRATernal+Lock-Free+Replication+for+Geo-Distributed+Transactions",
    "Viewstamped Replication Revisited": "https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/vr-revisited.pdf",
    "Raft: In Search of an Understandable Consensus Algorithm": "https://www.usenix.org/system/files/conference/atc14/atc14-paper-ongaro.pdf",
    "ZooKeeper: Wait-free Coordination for Internet-scale Systems": "https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf",
    "The Chubby Lock Service": "https://research.google.com/archive/chubby-osdi06.pdf",
    "Chain Replication for Supporting High Throughput and Availability": "https://www.usenix.org/legacy/event/osdi04/tech/full_papers/renesse/renesse.pdf",
    "Paxos Made Simple": "https://lamport.azurewebsites.net/pubs/paxos-simple.pdf",
    "Paxos Made Practical": "https://research.google.com/archive/paxos_made_live.pdf",
    "Flexible Paxos": "https://arxiv.org/pdf/1608.06696.pdf",
    "EPaxos: Egalitarian Paxos": "https://doi.org/10.1145/2517349.2517350",
    "Vertical Paxos": "https://lamport.org/pubs/vertical-paxos.pdf",
    "The Log-Structured Merge-Tree (LSM-Tree)": "https://doi.org/10.1007/s002360050048",
    "WiscKey: Separating Keys from Values in SSD-conscious Storage": "https://www.usenix.org/system/files/conference/fast16/fast16-papers-lu.pdf",
    "WiredTiger: A High-Performance NoSQL Database Engine": "https://source.wiredtiger.com/",
    "C-Store: A Column-oriented DBMS": "https://www.cs.umd.edu/~abadi/papers/vldb.pdf",
    "Google File System": "https://static.googleusercontent.com/media/research.google.com/en//archive/gfs-sosp2003.pdf",
    "LevelDB": "https://github.com/google/leveldb",
    "InnoDB: The MySQL Storage Engine": "https://dev.mysql.com/doc/refman/8.0/en/innodb-storage-engine.html",
    "TPC-C, TPC-H Benchmarks": "https://www.tpc.org/",
    "TPCC, TPC-DS, TPC-H": "https://www.tpc.org/",
    "TPC-C, TPC-H, TPC-DS": "https://www.tpc.org/",
    "CAP Theorem": "https://www.comp.nus.edu.sg/~gilbert/pubs/BrewersConjecture-SigAct.pdf",
    "PACELC Theorem": "https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf",
    "PACELC": "https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf",
    "Calvin: Fast Distributed Transactions": "https://www.cs.yale.edu/homes/thomson/publications/calvin-sigmod12.pdf",
    "Spanner’s Consistency": "https://www.usenix.org/system/files/conference/osdi12/osdi12-final-16.pdf",
    "FaunaDB: Calvin at global scale": "https://fauna.com/blog/demystifying-correctness-in-a-globally-distributed-database",
    "MegaStore and Megastore extended consistency": "https://www.cidrdb.org/cidr2011/Papers/CIDR11_Paper32.pdf",
    "Troe: Dynamic Transaction Redirect on Mobile": "https://scholar.google.com/scholar?q=Dynamic+Transaction+Redirect+on+Mobile",
    "Weak Consistency Models Survey": "https://scholar.google.com/scholar?q=Weak+Consistency+Models+Survey",
    "Global Secondary Indexes in F1": "https://www.vldb.org/pvldb/vol6/p1068-shute.pdf",
    "Dremel: Interactive Analysis of Web-Scale Datasets": "https://www.vldb.org/pvldb/vol3/R29.pdf",
    "RocksDB: Evolution of Development Priorities in a Key-Value Store": "https://www.usenix.org/system/files/fast21-dong.pdf",
    "MADlib: Scalable SQL Analytics": "https://www.vldb.org/pvldb/vol5/p1700_joehellerstein_vldb2012.pdf",
    "Pig, Hive": "https://www.vldb.org/pvldb/vol2/vldb09-938.pdf",
    "Numas: In-network query processing": "https://arxiv.org/pdf/1502.07169.pdf",
    "SQL on NoSQL": "https://doi.org/10.1007/978-3-031-27908-9",
    "YCSB: Yahoo! Cloud Serving Benchmark": "https://pages.cs.wisc.edu/~akella/CS838/F12/838-CloudPapers/ycsb.pdf",
    "LinkBench: A DB Benchmark Based on the Facebook Social Graph": "https://doi.org/10.1145/2463676.2465296",
    "OLTP-Bench": "https://www.vldb.org/pvldb/vol7/p277-difallah.pdf",
    "Wikipedia Trace Characterization": "https://scholar.google.com/scholar?q=Wikipedia+Trace+Characterization",
    "Bigtable vs. Cassandra vs. Dynamo": "https://link.springer.com/content/pdf/10.1631/FITEE.1500441.pdf",
    "Amazon SimpleDB": "https://docs.aws.amazon.com/AmazonSimpleDB/latest/DeveloperGuide/",
    "O’Neill": "https://doi.org/10.1007/s002360050048",
    "MongoDB architecture": "https://www.mongodb.com/resources/basics/databases/mongodb-architecture",
    "Azure Cosmos DB": "https://learn.microsoft.com/azure/cosmos-db/introduction",
    "Aerospike": "https://aerospike.com/docs/database/",
    "Part-Time Parliament": "https://lamport.org/pubs/lamport-paxos.pdf",
    "Viewstamped Replication": "https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/vr-revisited.pdf",
    "TOTALSTORE: Combining Paxos with Batch Processing": "https://research.google.com/archive/paxos_made_live.pdf",
    "LSM-Tree": "https://doi.org/10.1007/s002360050048",
    "WiscKey": "https://www.usenix.org/system/files/conference/fast16/fast16-papers-lu.pdf",
    "InnoDB": "https://dev.mysql.com/doc/refman/8.0/en/innodb-storage-engine.html",
    "LLAMA": "https://doi.org/10.1145/1989323.1989424",
    "BP-trees / fractal trees": "https://doi.org/10.1145/1463434.1463435",
    "SILT": "https://www.cs.cmu.edu/~dga/papers/silt-sosp2011.pdf",
    "HyperDex": "https://www.cs.cornell.edu/people/egs/papers/hyperdex-sigcomm.pdf",
    "ACID vs BASE": "https://queue.acm.org/detail.cfm?id=1394128",
    "CALM Theorem": "https://arxiv.org/pdf/1901.01930.pdf",
    "RedBlue consistency": "https://www.cs.cornell.edu/courses/cs5414/2017fa/papers/red-blue.pdf",
    "TAPIR": "https://homes.cs.washington.edu/~arvind/papers/tapir.pdf",
    "Consistency without Partition": "https://arxiv.org/pdf/1203.3544.pdf",
    "Secondary Indexes in Distributed DBs": "https://www.vldb.org/pvldb/vol6/p1068-shute.pdf",
    "Query2": "https://scholar.google.com/scholar?q=Query2+CIDR+2017",
    "Trill": "https://doi.org/10.14778/2735496.2735503",
    "Hyper": "https://doi.org/10.14778/2002938.2002940",
    "LINE": "https://arxiv.org/pdf/1503.03578.pdf",
    "SystemML, Spark SQL": "https://people.csail.mit.edu/matei/papers/2015/sigmod_spark_sql.pdf",
    "TailBench": "https://doi.org/10.1145/3297858.3304005",
    "HelloDB": "https://en.wikipedia.org/wiki/Hello_world_program",
    "Consistent Hashing": "https://www.cs.princeton.edu/courses/archive/fall09/cos518/papers/chash.pdf",
}

ALIAS_TITLES_RAW = {
    "Benchmarking Cloud Serving Systems with YCSB.": "YCSB: Yahoo! Cloud Serving Benchmark",
    "Fast Distributed Transactions and Strongly Consistent Replication for OLTP Database Systems.": "Calvin: Fast Distributed Transactions",
    "In Search of an Understandable Consensus Algorithm.": "Raft: In Search of an Understandable Consensus Algorithm",
    "ZooKeeper: Wait-free Coordination": "ZooKeeper: Wait-free Coordination for Internet-scale Systems",
    "Chain Replication": "Chain Replication for Supporting High Throughput and Availability",
    "YCSB": "YCSB: Yahoo! Cloud Serving Benchmark",
    "LinkBench": "LinkBench: A DB Benchmark Based on the Facebook Social Graph",
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
ALIAS_TITLES = {normalize_title(k): v for k, v in ALIAS_TITLES_RAW.items()}


def canonicalize_title(title: str) -> str:
    alias = ALIAS_TITLES.get(normalize_title(title))
    return alias if alias else title


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
    fallback_url = None
    for candidate_url in pick_download_urls(best_work):
        if fallback_url is None:
            fallback_url = candidate_url
        if not looks_like_pdf_url(candidate_url):
            continue
        verified_url = verify_downloadable_pdf(session, candidate_url)
        if verified_url:
            break

    download_url = verified_url or fallback_url
    if not download_url:
        return None

    return {
        "query_title": citation.title,
        "query_year": citation.year,
        "matched_title": best_work.get("display_name"),
        "matched_year": best_work.get("publication_year"),
        "score": round(best_score, 3),
        "openalex_id": best_work.get("id"),
        "download_url": download_url,
        "verified": bool(verified_url),
    }


def to_markdown(found: list[dict], unresolved: list[Citation]) -> str:
    lines = []
    lines.append("# Research Paper Download Links")
    lines.append("")
    lines.append("Generated from citations in `temp/research-papers.md` via OpenAlex lookup.")
    lines.append("")
    lines.append("## Resolved")
    lines.append("")
    lines.append("| # | Query Title | Matched Title | Year | Score | Verified | Download Link |")
    lines.append("|---|---|---|---:|---:|---|---|")
    for idx, item in enumerate(found, start=1):
        lines.append(
            f"| {idx} | {item['query_title']} | {item['matched_title']} | "
            f"{item.get('matched_year') or ''} | {item['score']} | "
            f"{'yes' if item.get('verified') else 'no'} | {item['download_url']} |"
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
    found_titles: set[str] = set()

    for citation in citations:
        canonical_title = canonicalize_title(citation.title)
        norm_citation = normalize_title(citation.title)
        norm_canonical = normalize_title(canonical_title)

        manual_link = MANUAL_LINKS.get(norm_citation) or MANUAL_LINKS.get(norm_canonical)
        if manual_link:
            verified_manual = verify_downloadable_pdf(session, manual_link)
            final_manual = verified_manual or manual_link
            found.append(
                {
                    "query_title": citation.title,
                    "query_year": citation.year,
                    "matched_title": canonical_title,
                    "matched_year": citation.year,
                    "score": 1.0 if verified_manual else 0.9,
                    "openalex_id": "manual",
                    "download_url": final_manual,
                    "verified": bool(verified_manual),
                }
            )
            found_titles.add(norm_citation)
            print(
                f"[FOUND] {citation.title} -> {final_manual} "
                f"({'manual' if verified_manual else 'manual-unverified'})"
            )
            time.sleep(args.delay)
            continue

        try:
            query_citation = (
                Citation(title=canonical_title, year=citation.year, raw_line=citation.raw_line)
                if canonical_title != citation.title
                else citation
            )
            result = query_openalex(session, query_citation)
        except requests.RequestException:
            result = None

        if result:
            result["query_title"] = citation.title
            found.append(result)
            found_titles.add(norm_citation)
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

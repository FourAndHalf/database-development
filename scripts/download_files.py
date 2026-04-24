#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = "Mozilla/5.0 (ResearchCrawler)"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_json_path() -> Path:
    return project_root() / "temp" / "research-paper-links.json"


def default_output_dir() -> Path:
    return project_root() / "data" / "raw_pdfs"


def is_pdf_response(response: requests.Response, url: str) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    if "application/pdf" in content_type:
        return True
    return urlparse(url).path.lower().endswith(".pdf")


def download_pdf(
    session: requests.Session,
    url: str,
    output_path: Path,
    timeout: int,
) -> int:
    with session.get(url, allow_redirects=True, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        if not is_pdf_response(response, response.url):
            raise ValueError(
                f"URL did not return a PDF: {url} (content-type={response.headers.get('content-type')})"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as file_obj:
            total = 0
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_obj.write(chunk)
                    total += len(chunk)
            return total


def generate_filename(title: str) -> str:
    # Remove special characters and replace spaces with underscores
    clean_title = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "_", clean_title) + ".pdf"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download paper PDFs listed in a JSON file.")
    parser.add_argument(
        "--json-file",
        type=Path,
        default=default_json_path(),
        help="Path to JSON file containing links.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir(),
        help="Directory where PDFs will be saved.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between downloads.",
    )
    args = parser.parse_args()

    json_path = args.json_file.resolve()
    if not json_path.exists():
        print(f"JSON file not found: {json_path}")
        return 1

    with open(json_path, 'r+') as f:
        data = json.load(f)
        resolved_papers = data.get("resolved", [])

        if not resolved_papers:
            print(f"No papers found in {json_path}")
            return 0

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        existing_files = {f.stem for f in output_dir.glob("*.pdf")}
        download_list = [
            paper for paper in resolved_papers
            if paper.get("download_url") and paper.get("verified")
        ]
        
        print(f"Found {len(download_list)} papers to potentially download.")

        for paper in download_list:
            title = paper.get("matched_title")
            if not title:
                print("Skipping paper with no title.")
                continue

            filename_stem = Path(generate_filename(title)).stem

            if filename_stem in existing_files:
                paper["download_status"] = "downloaded"
                print(f"[SKIP] Exists: {title}")
                continue

            if paper.get("download_status") == "downloaded":
                print(f"[SKIP] Already marked as downloaded: {title}")
                continue

            try:
                destination = output_dir / f"{filename_stem}.pdf"
                size = download_pdf(session, paper["download_url"], destination, args.timeout)
                paper["download_status"] = "downloaded"
                print(f"[DOWNLOADED] {destination} ({size} bytes)")
            except Exception as e:
                paper["download_status"] = f"failed: {e}"
                print(f"[FAILED] {title} -> {e}")

            time.sleep(args.delay)

        # Update the original data with the changes
        for i, original_paper in enumerate(data.get("resolved", [])):
            for updated_paper in download_list:
                if original_paper.get("query_title") == updated_paper.get("query_title"):
                    data["resolved"][i] = updated_paper
                    break
        
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
        
    downloaded_count = len([p for p in download_list if p.get("download_status") == "downloaded"])
    print(f"Finished. Total papers processed: {len(download_list)}. Total downloaded now: {downloaded_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

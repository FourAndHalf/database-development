#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = "Mozilla/5.0 (ResearchCrawler)"
URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+")

# Known replacements for links that are often stale in older notes.
KNOWN_REPLACEMENTS = {
    "https://research.google.com/archive/bigtable-osdi06.pdf": (
        "https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf"
    ),
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_markdown_path() -> Path:
    return project_root() / "temp" / "research-papers.md"


def default_output_dir() -> Path:
    return project_root() / "data" / "raw_pdfs"


def clean_url(raw_url: str) -> str:
    return raw_url.rstrip(".,;:!?)]}")


def looks_templated(url: str) -> bool:
    return "{" in url or "}" in url


def extract_urls(markdown_text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in URL_PATTERN.finditer(markdown_text):
        url = clean_url(match.group(0))
        if looks_templated(url):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def candidate_repairs(url: str) -> list[str]:
    candidates = [url]
    replacement = KNOWN_REPLACEMENTS.get(url)
    if replacement:
        candidates.append(replacement)

    parsed = urlparse(url)
    if parsed.netloc == "research.google.com" and parsed.path.startswith("/archive/"):
        candidates.append(
            f"https://static.googleusercontent.com/media/research.google.com/en/{parsed.path}"
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def is_pdf_response(response: requests.Response, url: str) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    if "application/pdf" in content_type:
        return True
    return urlparse(url).path.lower().endswith(".pdf")


def probe_url(session: requests.Session, url: str, timeout: int) -> tuple[bool, str]:
    try:
        head = session.head(url, allow_redirects=True, timeout=timeout)
        final_url = head.url
        if head.status_code < 400 and is_pdf_response(head, final_url):
            return True, final_url
    except requests.RequestException:
        pass

    try:
        get = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
        final_url = get.url
        ok = get.status_code < 400 and is_pdf_response(get, final_url)
        get.close()
        return ok, final_url
    except requests.RequestException:
        return False, url


def filename_from_url(url: str, index: int) -> str:
    name = Path(urlparse(url).path).name
    if not name:
        name = f"paper_{index:03d}.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


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


def replace_links_in_markdown(markdown_text: str, replacements: dict[str, str]) -> str:
    updated = markdown_text
    for old_url, new_url in replacements.items():
        updated = updated.replace(old_url, new_url)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Download paper PDFs listed in a markdown file.")
    parser.add_argument(
        "--markdown",
        type=Path,
        default=default_markdown_path(),
        help="Path to markdown file containing links.",
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
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist.",
    )
    args = parser.parse_args()

    markdown_path = args.markdown.resolve()
    if not markdown_path.exists():
        print(f"Markdown file not found: {markdown_path}")
        return 1

    markdown_text = markdown_path.read_text(encoding="utf-8")
    original_urls = extract_urls(markdown_text)
    if not original_urls:
        print(f"No URLs found in {markdown_path}")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    fixed_links: dict[str, str] = {}
    valid_urls: list[str] = []
    broken_urls: list[str] = []

    for url in original_urls:
        resolved_url = None
        for candidate in candidate_repairs(url):
            ok, final_url = probe_url(session, candidate, args.timeout)
            if ok:
                resolved_url = final_url
                break
        if resolved_url is None:
            broken_urls.append(url)
            print(f"[BROKEN] {url}")
            continue

        if resolved_url != url:
            fixed_links[url] = resolved_url
            print(f"[FIXED] {url} -> {resolved_url}")
        else:
            print(f"[OK] {url}")
        valid_urls.append(resolved_url)

    if fixed_links:
        updated_text = replace_links_in_markdown(markdown_text, fixed_links)
        markdown_path.write_text(updated_text, encoding="utf-8")
        print(f"Updated broken links in {markdown_path}")

    if not valid_urls:
        print("No valid PDF URLs to download.")
        return 1

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    failed = 0

    for index, url in enumerate(valid_urls, start=1):
        filename = filename_from_url(url, index)
        destination = output_dir / filename

        if args.skip_existing and destination.exists():
            print(f"[SKIP] Exists: {destination}")
            continue

        try:
            size = download_pdf(session, url, destination, args.timeout)
            downloaded += 1
            print(f"[DOWNLOADED] {destination} ({size} bytes)")
        except (requests.RequestException, ValueError) as exc:
            failed += 1
            print(f"[FAILED] {url} -> {exc}")
        time.sleep(args.delay)

    print(f"\nSummary: {downloaded} downloaded, {failed} failed, {len(broken_urls)} broken links.")
    if broken_urls:
        print("Broken URLs:")
        for url in broken_urls:
            print(f"- {url}")

    return 0 if failed == 0 and not broken_urls else 1


if __name__ == "__main__":
    raise SystemExit(main())

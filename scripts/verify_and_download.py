
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from googlesearch import search

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
    clean_title = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "_", clean_title) + ".pdf"

def find_pdf_link(query: str) -> str | None:
    """Searches for a PDF link for the given query."""
    try:
        # More specific search query
        search_query = f'"{query}" official paper filetype:pdf'
        for url in search(search_query, num_results=5):
            if url.endswith(".pdf"):
                return url
    except Exception as e:
        print(f"Error during web search for '{query}': {e}")
    return None

def main():
    json_path = default_json_path()
    if not json_path.exists():
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, 'r+') as f:
        data = json.load(f)
        resolved_papers = data.get("resolved", [])
        unverified_papers = [p for p in resolved_papers if not p.get("verified")]

        if not unverified_papers:
            print("No unverified papers found.")
            return

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        output_dir = default_output_dir()

        for paper in unverified_papers:
            title = paper.get("matched_title")
            if not title:
                continue

            print(f"Processing unverified paper: {title}")
            paper["download_status"] = "working"

            new_url = find_pdf_link(title)

            if new_url:
                print(f"Found new URL: {new_url}")
                paper["download_url"] = new_url
                try:
                    filename = generate_filename(title)
                    destination = output_dir / filename
                    download_pdf(session, new_url, destination, 30)
                    paper["verified"] = True
                    paper["download_status"] = "completed"
                    print(f"Successfully downloaded and verified: {title}")
                except Exception as e:
                    paper["download_status"] = f"failed: {e}"
                    print(f"Failed to download from new URL: {e}")
            else:
                paper["download_status"] = "failed: no new link found"
                print("No new PDF link found.")

            time.sleep(2)  # To avoid getting blocked

        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

if __name__ == "__main__":
    main()

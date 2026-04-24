
import json
import os
import re
from pathlib import Path

def generate_filename(title: str) -> str:
    """Generates a clean filename from a title."""
    clean_title = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "_", clean_title)

def find_and_remove_duplicates():
    """Finds and removes duplicate files based on the JSON data."""
    json_path = Path("temp/research-paper-links.json")
    if not json_path.exists():
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    resolved_papers = data.get("resolved", [])
    if not resolved_papers:
        print("No papers found in the JSON file.")
        return

    output_dir = Path("data/raw_pdfs")
    if not output_dir.exists():
        print(f"Output directory not found: {output_dir}")
        return

    all_pdfs = [f.stem for f in output_dir.glob("*.pdf")]
    expected_filenames = {
        generate_filename(paper["matched_title"])
        for paper in resolved_papers
        if paper.get("matched_title")
    }

    files_to_delete = []

    for expected_name in expected_filenames:
        duplicates = [pdf for pdf in all_pdfs if pdf.startswith(expected_name)]
        if len(duplicates) > 1:
            # Keep the first one, mark the rest for deletion
            duplicates.sort() # Sort to ensure consistent ordering
            files_to_delete.extend(duplicates[1:])

    if not files_to_delete:
        print("No duplicate files found.")
        return

    print("Found the following duplicate files to delete:")
    for filename in files_to_delete:
        print(f"- {filename}.pdf")

    for filename in files_to_delete:
        try:
            file_path = output_dir / f"{filename}.pdf"
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")

if __name__ == "__main__":
    find_and_remove_duplicates()

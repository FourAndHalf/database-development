
import json
from pathlib import Path

def reset_download_status():
    """Resets the download status of all papers in the JSON file."""
    json_path = Path("temp/research-paper-links.json")
    if not json_path.exists():
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, 'r+') as f:
        data = json.load(f)
        resolved_papers = data.get("resolved", [])

        for paper in resolved_papers:
            if "download_status" in paper:
                paper["download_status"] = "pending"

        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    print("Download status for all papers has been reset to 'pending'.")

if __name__ == "__main__":
    reset_download_status()

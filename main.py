import argparse
import json
from pathlib import Path
from resume_screening.pipeline import screen_directory

def main():
    parser = argparse.ArgumentParser(description="Screen and rank resumes for Python + AI engineering roles.")
    parser.add_argument("--input", required=True, help="Directory containing PDF/DOCX/TXT resumes")
    parser.add_argument("--output", default="./output/results.json", help="Path to output JSON")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub enrichment")
    args = parser.parse_args()

    result = screen_directory(Path(args.input), enrich_github=not args.no_github)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Processed: {result['batch_summary']['total_resumes']}")
    print(f"Parsed: {result['batch_summary']['successfully_parsed']}")
    print(f"Eligible: {result['batch_summary']['eligible']}")
    print(f"Rejected: {result['batch_summary']['rejected']}")
    print(f"Failed/unreadable: {result['batch_summary']['failed_unreadable']}")
    print(f"Results written to: {output.resolve()}")

if __name__ == "__main__":
    main()

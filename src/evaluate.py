"""Run with uv run python src/evaluate.py request.json --output report.json."""
import argparse
import json
from pathlib import Path

from agents.evaluation import evaluate_document


def main():
    parser = argparse.ArgumentParser(description="기획서 정량 평가")
    parser.add_argument("request", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    report = evaluate_document(request)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

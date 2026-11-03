---
title: "src/evaluate.py"
tags:
  - code
  - layer/code
---

# `src/evaluate.py`

- **소속 계층 태그**: `#layer/code`
- **상위 아키텍처 노트**: [[00-Index]]
- **내부 모듈 의존성(Imports)**: [[mod__agents__evaluation]]

> Run with uv run python src/evaluate.py request.json --output report.json.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def main()`

## 소스 코드 미리보기 (`src/evaluate.py`)

```python
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
```

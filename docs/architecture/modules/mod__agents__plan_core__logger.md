---
title: "src/agents/plan_core/logger.py"
tags:
  - code
  - layer/agent
---

# `src/agents/plan_core/logger.py`

- **소속 계층 태그**: `#layer/agent`
- **상위 아키텍처 노트**: [[00-Index]], [[03-LangGraph-Agents]], [[langgraph-flow.canvas]]
- **내부 모듈 의존성(Imports)**: 없음

> 파이프라인 로깅 시스템

## 정의된 클래스 / 상태 스키마
- `LogLevel`
- `PipelineLogger`

## 정의된 함수 / 노드
- `def get_logger()`
- `def reset_logger()`

## 소스 코드 미리보기 (`src/agents/plan_core/logger.py`)

```python
"""
파이프라인 로깅 시스템
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class PipelineLogger:
    """파이프라인 실행 로그 기록"""
    
    def __init__(self, log_dir: str = "logs"):
        # 프로젝트 루트 경로 찾기 (src의 상위 디렉토리)
        project_root = Path(__file__).parent.parent.parent.parent
        self.log_dir = project_root / log_dir
        self.log_dir.mkdir(exist_ok=True)

        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"pipeline_{timestamp}.log"
        self.json_file = self.log_dir / f"pipeline_{timestamp}.json"
        
        self.logs: List[Dict[str, Any]] = []
        
    def log(self, level: LogLevel, stage: str, message: str, data: Dict[str, Any] = None):
        """로그 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "stage": stage,
            "message": message,
            "data": data or {}
        }
        
        self.logs.append(log_entry)
        
        # 텍스트 로그 파일에 기록
        with open(self.log_file, "a", encoding="utf-8") as f:
            log_line = f"[{log_entry['timestamp']}] [{level.value}] [{stage}] {message}\n"
            if data:
                log_line += f"  Data: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
            f.write(log_line)
    
    def log_section_generation(self, section_number: str, section_title: str, method: str):
        """섹션 생성 로그"""
        self.log(
            LogLevel.INFO,
            "section_generation",
            f"섹션 생성 시작: {section_number}. {section_title}",
            {"section_number": section_number, "title": section_title, "method": method}
        )
    
    def log_visual_decision(self, section_number: str, decision: Dict[str, Any]):
        """시각화 결정 로그"""
        needs = []
        if decision.get("needs_table"):
            needs.append(f"표({decision.get('table_type')})")
        if decision.get("needs_diagram"):
            needs.append(f"다이어그램({decision.get('diagram_type')})")
        if decision.get("needs_image_search"):
            needs.append("이미지 검색")
        if decision.get("needs_image_gen"):
            needs.append("이미지 생성")
        
        message = f"시각화 결정: {', '.join(needs) if needs else '없음'}"
        
        self.log(
            LogLevel.INFO,
            "visual_decision",
            message,
            {
                "section_number": section_number,
                "decision": decision,
                "reason": decision.get("reason", "")
            }
        )
    
    def log_visual_generation(self, section_number: str, visual_type: str, success: bool, error: str = None):
        """시각화 생성 로그"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"시각화 생성 {'성공' if success else '실패'}: {visual_type}"
```

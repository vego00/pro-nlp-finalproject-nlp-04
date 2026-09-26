# 기획서 정량 평가 에이전트

완성된 문서와 명시적인 평가 항목을 입력받아 항목별 판정·근거와 정량 지표를 JSON으로 반환한다.
기존 생성/수정 과정의 통과 판정과 별도로 실행한다. Supervisor 자동 라우팅이나 UI 연결은 포함하지 않는다.

```sh
uv run python src/evaluate.py examples/evaluation_request.json --output evaluation_report.json
```

기존 UPSTAGE_API_KEY 설정이 필요하다. 실제 평가는 LLM API를 호출한다.
Python에서는 `agents.evaluation.evaluate_document(request)`를 호출한다 (`src`가 import 경로에 있어야 한다).
LangGraph에서는 `graph.evaluation_graph.evaluation_subgraph.invoke(state)`를 사용한다.
`state.evaluation.request`에 평가 입력을 지정하며, document가 생략되면 `state.plan.final_markdown`을 사용한다.
결과는 `state.evaluation.report`에 저장한다. 오류나 잘못된 판정 응답은 예외로 전달하며 성공 점수로 대체하지 않는다.

## 입력 계약

`document`는 평가할 전체 문서이다. `original_input`에는 원래 사용자 요구를 넣는다.
모든 목록 항목은 `{ "id": "고유 ID", "text": "내용" }` 형식이며 목록 내 ID는 중복할 수 없다.
분모를 고정하기 위해 평가 항목을 호출자가 제공한다. 누락된 요구·주장을 자동으로 추출했다고 간주하지 않는다.
문서 간 비교에는 동일한 평가 항목 목록을 사용해야 한다.

| 입력 목록 | 평가 기준 |
| --- | --- |
| requirements | 전체 필수 요구사항 |
| claims | 검토할 주요 주장 |
| sources | 검증에 사용할 자료 본문 및 출처 정보. URL만으로 확인 처리하지 않음 |
| work_items | 명세·화면·API 초안을 작성할 후속 작업 항목 |
| edit_conditions | 충족해야 할 수정 조건 |
| preservation_items | 수정 대상 밖에서 의미를 보존해야 할 항목 |
| visual_elements | 평가할 표/다이어그램 요소. 실제 코드·내용을 document 또는 항목에 포함 |

수정 평가에는 `original_document`가 필수다. 스크린샷·파일 경로만으로 시각화 내용을 판독하지 않는다.
빈 목록은 해당 평가를 지정하지 않은 것으로 처리한다. 항목이 없다면 비율은 `null`이며 status는 `not_applicable`이다.

## 계산 규칙

비율은 0–1이며 분자·분모를 함께 반환한다. 표시용 백분율은 value × 100이다.

| 출력 지표 | 계산 |
| --- | --- |
| requirement_coverage | 정확히 반영된 필수 항목 / 전체 필수 항목 |
| claim_verification | 입력 또는 자료로 검증된 주장 / 검토한 주장 |
| consistency | 모순 건수 및 모순 건수 × 10 / 필수 요구사항 수 |
| usability | 추가 질문 없이 초안 작성 가능한 작업 항목 / 전체 작업 항목 |
| edit_accuracy | 충족된 수정 조건 / 전체 수정 조건 |
| unintended_change_rate | 의미가 변경된 보존 항목 / 전체 보존 항목 (낮을수록 좋음) |
| visual_accuracy | 본문·입력과 일치하는 요소 / 평가할 시각화 요소 |
| visual_omission_count, visual_wrong_connection_count | 누락 및 잘못된 연결의 개별 건수 |

주장은 `input_verified`, `source_verified`, `explicit_assumption`, `unsupported` 네 범주로 보고한다.
명시된 가정은 검증률 분자에 포함하지 않는다. 시각화 평가 항목이 없으면 시각화 오류 건수도 null이다.
모순은 문서 전체에서 검사하며 요구사항 수가 0이면 10개당 건수만 null이다.

판단은 LLM 기반이므로 근거 검토와 사람의 교차 검증이 필요하다. 코드는 ID 누락·중복과 잘못된 자료 참조를 거부하고 계산을 수행한다.
현재 버전은 외부 자료를 직접 검색하지 않으며 실제 후속 작업의 완료율·소요 시간을 측정하지 않는다.
종합 점수나 합격 기준은 별도 가중치 합의가 없어 제공하지 않는다.

```sh
uv run pytest tests/test_evaluation.py
```

테스트는 LLM 호출 없이 계산, 누락·중복 거부, 근거 참조 검증, 상태 어댑터를 확인한다.

현재 저장소의 기존 `uv.lock`에는 python-dotenv 중복 항목이 있어 uv 버전에 따라 파싱이 실패할 수 있다.
이 경우 프로젝트 잠금 파일과 분리된 환경에서 아래 명령을 사용할 수 있다.

```sh
uv run --no-project --with pytest --with pydantic --with langgraph python -m pytest tests/test_evaluation.py
uv run --no-project --with pydantic --with langchain-upstage --with python-dotenv python src/evaluate.py examples/evaluation_request.json --output evaluation_report.json
```

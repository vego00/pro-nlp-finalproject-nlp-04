import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.evaluation import evaluate_document, evaluation_node
from agents.evaluation_core.metrics import calculate_metrics
from agents.evaluation_core.schemas import Assessment, EvaluationInput


def judgment(id, passed=True):
    return dict(id=id, passed=passed, reason="판정 이유", evidence="문서 1절")


def assessment(**updates):
    data = {key: [] for key in Assessment.model_fields}
    data.update(updates)
    return Assessment(**data)


def test_all_metrics():
    inputs = EvaluationInput(
        document="수정 문서", original_document="이전 문서", original_input="사용자 입력",
        sources=[dict(id="s1", text="자료 본문")],
        **{key: [dict(id=f"{key}{i}", text="평가 항목") for i in range(count)]
           for key, count in dict(requirements=2, claims=4, work_items=2,
                                  edit_conditions=2, preservation_items=2, visual_elements=2).items()},
    )
    result = assessment(
        **{key: [judgment(f"{key}0"), judgment(f"{key}1", False)] for key in (
            "requirements", "work_items", "edit_conditions", "preservation_items", "visual_elements")},
        claims=[dict(id=f"claims{i}", category=category, reason="이유", evidence="인용",
                     source_ids=["s1"] if i == 1 else [])
                for i, category in enumerate(["input_verified", "source_verified", "explicit_assumption", "unsupported"])],
        contradictions=[dict(id="c1", description="필드 형식 충돌", locations=["API", "모델"])],
        visual_omissions=[dict(id="v1", description="노드 누락", locations=["그림 1"])],
        visual_wrong_connections=[dict(id="v2", description="연결 오류", locations=["그림 1"])],
    )
    metrics = calculate_metrics(inputs, result)
    for key in ("requirement_coverage", "claim_verification", "usability", "edit_accuracy",
                "unintended_change_rate", "visual_accuracy"):
        assert metrics[key]["value"] == 0.5
    assert metrics["consistency"]["per_10_requirements"] == 5
    assert metrics["visual_omission_count"] == metrics["visual_wrong_connection_count"] == 1
    assert metrics["claim_categories"]["explicit_assumption"] == 1


def test_empty_denominators_are_not_perfect_scores():
    metrics = calculate_metrics(EvaluationInput(document="문서"), assessment())
    assert metrics["requirement_coverage"] == dict(numerator=0, denominator=0, value=None, status="not_applicable")
    assert metrics["consistency"]["per_10_requirements"] is None
    assert metrics["visual_omission_count"] is None


@pytest.mark.parametrize("judgments", [[], [judgment("wrong")], [judgment("r"), judgment("r")]])
def test_reject_incomplete_or_duplicate_coverage(judgments):
    inputs = EvaluationInput(document="문서", requirements=[dict(id="r", text="요구")])
    with pytest.raises(ValueError, match="judgments"):
        calculate_metrics(inputs, assessment(requirements=judgments))


@pytest.mark.parametrize("source_ids", [[], ["invented"]])
def test_reject_unverifiable_source_reference(source_ids):
    inputs = EvaluationInput(document="문서", claims=[dict(id="c", text="주장")])
    with pytest.raises(ValueError, match="source"):
        calculate_metrics(inputs, assessment(claims=[dict(
            id="c", category="source_verified", source_ids=source_ids, reason="이유", evidence="인용")]))


def test_edit_requires_baseline_and_unique_inventory():
    with pytest.raises(ValueError, match="original_document"):
        EvaluationInput(document="문서", edit_conditions=[dict(id="e", text="수정")])
    with pytest.raises(ValueError, match="Duplicate"):
        EvaluationInput(document="문서", requirements=[dict(id="r", text="요구")] * 2)


def test_agent_uses_structured_judgments():
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = assessment()
    report = evaluate_document({"document": "문서"}, llm=llm)
    assert report["input"]["document"] == "문서"
    assert report["schema_version"] == "1.0"
    llm.with_structured_output.assert_called_once_with(Assessment)


def test_node_preserves_document_and_only_updates_evaluation(monkeypatch):
    import agents.evaluation as module
    monkeypatch.setattr(module, "evaluate_document", lambda request: {"document": request["document"]})
    state = {"plan": {"final_markdown": "완성된 기획서"}, "evaluation": {"request": {}}}
    result = evaluation_node(state)
    assert set(result) == {"evaluation"}
    assert result["evaluation"]["report"]["document"] == "완성된 기획서"
    assert state["evaluation"]["request"] == {}


def test_compiled_graph_keeps_plan_and_returns_report(monkeypatch):
    import agents.evaluation as module
    from graph.evaluation_graph import evaluation_subgraph

    monkeypatch.setattr(module, "evaluate_document", lambda request: {"document": request["document"]})
    state = {"plan": {"final_markdown": "기획서"}, "evaluation": {"request": {}}}
    result = evaluation_subgraph.invoke(state)
    assert result["plan"] == state["plan"]
    assert result["evaluation"]["report"] == {"document": "기획서"}

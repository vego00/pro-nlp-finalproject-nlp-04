"""Quantitative document evaluator, usable independently or as a graph node."""
from agents.evaluation_core.metrics import calculate_metrics
from agents.evaluation_core.schemas import Assessment, EvaluationInput
from prompts.evaluation_prompts import EVALUATION_PROMPT


def evaluate_document(inputs: EvaluationInput | dict, llm=None) -> dict:
    inputs = EvaluationInput.model_validate(inputs)
    if llm is None:
        from models.llm import get_llm
        llm = get_llm(temperature=0)
    response = llm.with_structured_output(Assessment).invoke([
        ("system", EVALUATION_PROMPT),
        ("human", inputs.model_dump_json()),
    ])
    assessment = Assessment.model_validate(response)
    return {
        "schema_version": "1.0",
        "method": "llm_judgment_deterministic_metrics",
        "input": inputs.model_dump(),
        "metrics": calculate_metrics(inputs, assessment),
        "assessment": assessment.model_dump(),
    }


def evaluation_node(state: dict) -> dict:
    """Explicit inventories live in evaluation.request; plan supplies the document."""
    evaluation = state.get("evaluation", {})
    request = dict(evaluation.get("request", {}))
    request.setdefault("document", state.get("plan", {}).get("final_markdown", ""))
    return {"evaluation": {"request": request, "report": evaluate_document(request)}}

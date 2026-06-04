from typing import TypedDict, Any, Annotated
import operator


def merge_dicts(a: dict, b: dict) -> dict:
    d = dict(a)
    d.update(b)
    return d


def first_non_default(default: str = "") -> callable:
    def reducer(a: str, b: str) -> str:
        if b and b != default and b != a:
            return b
        return a or b
    return reducer


status_reducer = first_non_default("running")
error_reducer = first_non_default("")


def last_wins(a: Any, b: Any) -> Any:
    return b if b else a


class WorkflowState(TypedDict):
    execution_id: int
    messages: Annotated[list[dict], operator.add]
    node_results: Annotated[dict[str, Any], merge_dicts]
    completed_nodes: Annotated[list[str], operator.add]
    input_data: dict
    output_data: Annotated[dict, merge_dicts]
    status: Annotated[str, status_reducer]
    error: Annotated[str, error_reducer]
    # Shared memory for pipeline processing
    raw_text: Annotated[str, last_wins]
    sections: Annotated[dict, merge_dicts]
    extracted_skills: Annotated[dict, merge_dicts]
    extracted_experience: Annotated[list, operator.add]
    extracted_education: Annotated[list, operator.add]
    pipeline_score: Annotated[dict, merge_dicts]
    pipeline_output: Annotated[list, operator.add]

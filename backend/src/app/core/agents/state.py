from typing import TypedDict


class QAState(TypedDict, total=False):
    question: str
    top_k: int
    context: str
    answer: str
    citations: dict[str, dict] | None

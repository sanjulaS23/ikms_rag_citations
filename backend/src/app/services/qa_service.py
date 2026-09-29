from app.core.agents.agents import get_graph
from app.utils.logging import get_logger


logger = get_logger(__name__)


def run_qa(question: str, top_k: int = 4) -> dict:
    graph = get_graph()
    result = graph.invoke({"question": question, "top_k": top_k})
    response = {
        "answer": result.get("answer", ""),
        "context": result.get("context", ""),
        "citations": result.get("citations"),
    }
    logger.info("QA response ready")
    return response

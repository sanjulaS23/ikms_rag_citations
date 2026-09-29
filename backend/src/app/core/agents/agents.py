import os
from functools import lru_cache

from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from app.core.agents.prompts import ANSWER_PROMPT, VERIFICATION_PROMPT
from app.core.agents.state import QAState
from app.core.retrieval.retriever import retrieve_chunks
from app.core.retrieval.serialization import serialize_chunks_with_ids
from app.utils.logging import get_logger
from app.utils.text import extract_citation_ids, remove_invalid_citations


logger = get_logger(__name__)


def _retrieve_node(state: QAState) -> QAState:
    docs = retrieve_chunks(state["question"], state.get("top_k", 4))
    context, citation_map = serialize_chunks_with_ids(docs)
    return {"context": context, "citations": citation_map}


def _answer_node(state: QAState) -> QAState:
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "gemma3:12b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.2,
    )
    messages = ANSWER_PROMPT.format_messages(
        question=state["question"],
        context=state.get("context", ""),
    )
    response = llm.invoke(messages)
    answer = getattr(response, "content", "") or ""
    logger.info("Citations used in answer: %s", ", ".join(extract_citation_ids(answer)))
    return {"answer": answer}


def _verify_node(state: QAState) -> QAState:
    citations = state.get("citations") or {}
    valid_ids = sorted(citations.keys())
    if not valid_ids:
        return {"answer": state.get("answer", "")}

    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "gemma3:12b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.1,
    )
    messages = VERIFICATION_PROMPT.format_messages(
        valid_ids=", ".join(valid_ids),
        context=state.get("context", ""),
        answer=state.get("answer", ""),
    )
    response = llm.invoke(messages)
    cleaned = remove_invalid_citations(getattr(response, "content", "") or "", valid_ids)
    logger.info("Verification completed. Final citations: %s", ", ".join(extract_citation_ids(cleaned)))
    return {"answer": cleaned}


@lru_cache(maxsize=1)
def get_graph():
    graph = StateGraph(QAState)
    # Node IDs must not match QAState field names in LangGraph.
    graph.add_node("retrieve_docs", _retrieve_node)
    graph.add_node("generate_answer", _answer_node)
    graph.add_node("verify_answer", _verify_node)

    graph.set_entry_point("retrieve_docs")
    graph.add_edge("retrieve_docs", "generate_answer")
    graph.add_edge("generate_answer", "verify_answer")
    graph.add_edge("verify_answer", END)

    return graph.compile()

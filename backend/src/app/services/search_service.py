from app.core.retrieval.retriever import retrieve_chunks
from app.utils.logging import get_logger


logger = get_logger(__name__)


def search_pdfs(query: str, top_k: int = 5, namespace: str | None = None) -> dict:
    """Search indexed PDFs using vector similarity."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be between 1 and 50")

    try:
        docs = retrieve_chunks(query, top_k)
        logger.info("Retrieved %d documents for query: %s", len(docs), query)

        results = []
        for doc in docs:
            meta = doc.metadata or {}
            results.append({
                "content": doc.page_content,
                "page": meta.get("page", meta.get("page_number")),
                "source": meta.get("source", meta.get("filename", "unknown")),
                "score": meta.get("score", 0.0)
            })

        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as exc:
        logger.error("Search failed for query '%s': %s", query, exc)
        raise

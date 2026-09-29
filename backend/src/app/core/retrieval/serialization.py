from typing import Tuple
from langchain_core.documents import Document

from app.utils.logging import get_logger


logger = get_logger(__name__)


def _truncate_snippet(text: str, limit: int = 150) -> str:
    safe = (text or "").replace("\n", " ").strip()
    if len(safe) <= limit:
        return safe
    return safe[:limit].rstrip() + "..."


def serialize_chunks_with_ids(docs: list[Document]) -> Tuple[str, dict]:
    context_parts: list[str] = []
    citation_map: dict[str, dict] = {}

    for idx, doc in enumerate(docs or [], start=1):
        chunk_id = f"C{idx}"
        meta = doc.metadata or {}
        page = meta.get("page", meta.get("page_number"))
        source = meta.get("source", meta.get("file_name", meta.get("filename")))
        snippet = _truncate_snippet(doc.page_content)

        citation_map[chunk_id] = {
            "page": page,
            "snippet": snippet,
            "source": source,
        }

        page_label = page if page is not None else "unknown"
        chunk_text = (doc.page_content or "").strip()
        context_parts.append(
            f"[{chunk_id}] Chunk from page {page_label}:\n{chunk_text}"
        )

    logger.info("Retrieved %d chunks", len(citation_map))
    logger.info("Generated chunk IDs: %s", ", ".join(citation_map.keys()))

    return "\n\n".join(context_parts), citation_map

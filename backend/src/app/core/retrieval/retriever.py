from langchain_core.documents import Document

from app.core.vectorstore.pinecone_store import get_vectorstore
from app.utils.logging import get_logger


logger = get_logger(__name__)


def retrieve_chunks(question: str, top_k: int) -> list[Document]:
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(question, k=top_k)
    logger.info("Retrieved %d docs for query", len(docs))
    return docs

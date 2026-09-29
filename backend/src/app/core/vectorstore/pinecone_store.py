import os
from pathlib import Path

from langchain_core.documents import Document

from app.utils.logging import get_logger


logger = get_logger(__name__)


class LocalVectorStore:
    """Simple local FAISS-backed vector store using Ollama embeddings."""

    def __init__(self, embeddings, index_dir: Path):
        self.embeddings = embeddings
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.store = self._load_store()

    def _load_store(self):
        try:
            from langchain_community.vectorstores import FAISS
        except ImportError as exc:
            raise RuntimeError("langchain-community must be installed for FAISS support") from exc

        candidates = [self.index_dir, self.index_dir / "index"]
        index_dir = next(
            (
                p
                for p in candidates
                if p.exists() and ((p / "index.faiss").exists() or (p / "index.pkl").exists())
            ),
            None,
        )

        if index_dir is None:
            logger.info("No FAISS index found at %s", self.index_dir)
            return None

        try:
            return FAISS.load_local(str(index_dir), self.embeddings, allow_dangerous_deserialization=True)
        except Exception as exc:
            logger.warning("Could not load FAISS index at %s: %s", index_dir, exc)
            return None

    def add_texts(self, texts, metadatas=None, namespace=None):
        if not texts:
            return 0

        try:
            from langchain_community.vectorstores import FAISS
        except ImportError as exc:
            raise RuntimeError("langchain-community must be installed for FAISS support") from exc

        metadata_list = metadatas or [{} for _ in texts]
        docs = [
            Document(page_content=text, metadata=meta or {})
            for text, meta in zip(texts, metadata_list)
        ]

        if self.store is None:
            self.store = FAISS.from_documents(docs, self.embeddings)
        else:
            self.store.add_documents(docs)

        self.store.save_local(str(self.index_dir))
        return len(texts)

    def similarity_search(self, query, k=4, **kwargs):
        if self.store is None:
            return []
        return self.store.similarity_search(query, k=k, **kwargs)


def get_vectorstore():
    """Create or load a local FAISS vectorstore."""
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError as exc:
        logger.error("Ollama embeddings library not installed: %s", exc)
        raise RuntimeError("langchain-ollama must be installed") from exc

    embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest").strip()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    embeddings = OllamaEmbeddings(model=embedding_model, base_url=base_url)

    project_root = Path(__file__).resolve().parents[5]
    index_dir = project_root / ".faiss_store"

    logger.info(
        "Using local FAISS vector store at %s with Ollama embedding model %s",
        index_dir,
        embedding_model,
    )
    return LocalVectorStore(embeddings=embeddings, index_dir=index_dir)

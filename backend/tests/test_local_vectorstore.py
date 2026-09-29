from pathlib import Path

from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.vectorstore.pinecone_store import LocalVectorStore


def test_local_vectorstore_loads_existing_faiss_index(tmp_path: Path):
    docs = [Document(page_content="alpha beta gamma", metadata={"source": "test.pdf", "page": 1})]
    embeddings = FakeEmbeddings(size=3)
    store = FAISS.from_documents(docs, embeddings)
    store.save_local(str(tmp_path))

    loaded = LocalVectorStore(embeddings, tmp_path)

    assert loaded.store is not None
    result = loaded.similarity_search("alpha", k=1)
    assert len(result) == 1
    assert result[0].page_content == docs[0].page_content

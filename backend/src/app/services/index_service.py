import os
from io import BytesIO
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.vectorstore.pinecone_store import get_vectorstore
from app.utils.logging import get_logger


logger = get_logger(__name__)


def index_pdf(file_path: str, namespace: str | None = None) -> dict:
    """Index a PDF file by extracting text, splitting chunks, and storing in Pinecone."""

    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if not file_path.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported")

    try:
        reader = PdfReader(file_path)
        if len(reader.pages) == 0:
            raise ValueError("PDF contains no pages")
    except Exception as exc:
        logger.error("Failed to read PDF: %s", exc)
        raise

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    texts: list[str] = []
    metas: list[dict] = []
    source = Path(file_path).name

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            if not page_text.strip():
                logger.warning("Page %d has no extractable text", page_num)
                continue

            for chunk in splitter.split_text(page_text):
                if chunk.strip():
                    texts.append(chunk)
                    metas.append({"page": page_num, "source": source})
        except Exception as exc:
            logger.error("Failed to process page %d: %s", page_num, exc)
            raise

    if not texts:
        raise ValueError("No extractable text found in PDF")

    try:
        vectorstore = get_vectorstore()
        vectorstore.add_texts(texts, metadatas=metas, namespace=namespace)
        logger.info("Successfully indexed %d chunks from %s into namespace %s", len(texts), source, namespace or "default")
    except Exception as exc:
        logger.error("Failed to store embeddings in Pinecone: %s", exc)
        raise

    return {"chunks_indexed": len(texts), "source": source, "pages": len(reader.pages)}


def index_pdf_from_bytes(file_bytes: bytes, filename: str, namespace: str | None = None) -> dict:
    """Index a PDF from bytes (useful for uploaded files)."""

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported")

    try:
        pdf_stream = BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)
        if len(reader.pages) == 0:
            raise ValueError("PDF contains no pages")
    except Exception as exc:
        logger.error("Failed to read PDF from bytes: %s", exc)
        raise

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    texts: list[str] = []
    metas: list[dict] = []

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            if not page_text.strip():
                logger.warning("Page %d has no extractable text", page_num)
                continue

            for chunk in splitter.split_text(page_text):
                if chunk.strip():
                    texts.append(chunk)
                    metas.append({"page": page_num, "source": filename})
        except Exception as exc:
            logger.error("Failed to process page %d: %s", page_num, exc)
            raise

    if not texts:
        raise ValueError("No extractable text found in PDF")

    try:
        vectorstore = get_vectorstore()
        vectorstore.add_texts(texts, metadatas=metas, namespace=namespace)
        logger.info("Successfully indexed %d chunks from %s into namespace %s", len(texts), filename, namespace or "default")
    except Exception as exc:
        logger.error("Failed to store embeddings in Pinecone: %s", exc)
        raise

    return {"chunks_indexed": len(texts), "source": filename, "pages": len(reader.pages)}

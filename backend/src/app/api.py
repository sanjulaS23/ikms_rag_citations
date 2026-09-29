from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
import os

from app.services.index_service import index_pdf, index_pdf_from_bytes
from app.services.qa_service import run_qa
from app.services.search_service import search_pdfs
from app.utils.logging import get_logger


logger = get_logger(__name__)

router = APIRouter()


# Debug Endpoint
@router.get("/debug/pinecone")
async def debug_pinecone():
    """Test Pinecone connection and environment variables."""
    try:
        from app.core.vectorstore.pinecone_store import get_vectorstore
        
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX")
        
        if not api_key:
            return {"status": "error", "message": "PINECONE_API_KEY not set"}
        if not index_name:
            return {"status": "error", "message": "PINECONE_INDEX not set"}
        
        # Try to connect
        vs = get_vectorstore()
        
        return {
            "status": "ok",
            "message": "Pinecone connected successfully",
            "index": index_name,
            "api_key_prefix": api_key[:20] + "..." if api_key else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "api_key_set": bool(os.getenv("PINECONE_API_KEY")),
            "index_set": bool(os.getenv("PINECONE_INDEX"))
        }


# QA Request/Response Models
class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(4, ge=1, le=20)


class QAResponse(BaseModel):
    answer: str
    context: str
    citations: dict[str, dict] | None


# Index Request/Response Models
class IndexRequest(BaseModel):
    file_path: str = Field(..., min_length=1)
    namespace: str | None = None


class IndexResponse(BaseModel):
    chunks_indexed: int
    source: str
    pages: int


# Search Request/Response Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)


class SearchResult(BaseModel):
    content: str
    page: int | None
    source: str
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    count: int


# QA Endpoint
@router.post("/qa", response_model=QAResponse)
async def qa_endpoint(payload: QARequest):
    """
    Q&A endpoint that retrieves relevant PDF chunks and generates evidence-aware answers with citations.
    """
    try:
        if not payload.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        return run_qa(payload.question, payload.top_k)
    except HTTPException:
        raise
    except Exception as exc:
        # OpenAI auth failures are common when env vars are stale or overridden.
        err_text = str(exc)
        if "invalid_api_key" in err_text or "Incorrect API key provided" in err_text:
            raise HTTPException(
                status_code=401,
                detail="OpenAI authentication failed. Verify OPENAI_API_KEY and restart the server.",
            ) from exc
        logger.exception("QA endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


# Index PDF from file path endpoint
@router.post("/index-pdf", response_model=IndexResponse)
async def index_pdf_endpoint(payload: IndexRequest):
    """
    Index a PDF file from a file path for later retrieval.
    """
    try:
        return index_pdf(payload.file_path, payload.namespace)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Index endpoint failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


# Index PDF from file upload endpoint
@router.post("/upload-pdf", response_model=IndexResponse)
async def upload_pdf_endpoint(file: UploadFile = File(...), namespace: str | None = None):
    """
    Upload and index a PDF file directly.
    """
    try:
        logger.info(f"Upload request: filename={file.filename}, content_type={file.content_type}")
        
        if file.content_type != "application/pdf":
            logger.warning(f"Invalid content type: {file.content_type}")
            raise HTTPException(status_code=400, detail="File must be a PDF")

        file_bytes = await file.read()
        logger.info(f"Read {len(file_bytes)} bytes from {file.filename}")
        
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File is empty")

        result = index_pdf_from_bytes(file_bytes, file.filename or "document.pdf", namespace)
        logger.info(f"Upload successful: {result}")
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        logger.error(f"ValueError during upload: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(f"CRITICAL ERROR during upload: {str(exc)}")
        import traceback
        print(f"FULL TRACEBACK:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)}") from exc


# Search endpoint
@router.post("/search", response_model=SearchResponse)
async def search_endpoint(payload: SearchRequest):
    """
    Search indexed PDFs using vector similarity.
    """
    try:
        if not payload.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = search_pdfs(payload.query, payload.top_k)
        return SearchResponse(
            query=result["query"],
            results=[SearchResult(**r) for r in result["results"]],
            count=result["count"]
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Search endpoint failed")
        print(f"🔴 SEARCH ERROR: {type(exc).__name__}: {str(exc)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(exc)[:100]}") from exc


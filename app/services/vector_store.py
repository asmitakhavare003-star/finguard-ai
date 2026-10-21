"""RAG vector storage helpers backed by Qdrant and OpenAI embeddings.

Provides PDF ingestion into a Qdrant collection and a similarity search that
filters on company and optional year metadata.
"""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
)

from app.core.config import settings
from app.schemas.financial import IngestResponse

logger = logging.getLogger(__name__)

COLLECTION_NAME = "financial_reports"
DEFAULT_PDF_PATH = "data/sample_10k.pdf"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_PDF_BYTES = 20 * 1024 * 1024


def _qdrant_api_key() -> Optional[str]:
    """Return the Qdrant API key string, or ``None`` when unset/empty."""
    if settings.QDRANT_API_KEY is None:
        return None
    value = settings.QDRANT_API_KEY.get_secret_value()
    return value or None


def _build_embeddings() -> OpenAIEmbeddings:
    """Create OpenAI embedding client from application settings."""
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )


def _qdrant_client() -> QdrantClient:
    """Open a Qdrant client from application settings."""
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=_qdrant_api_key(),
        timeout=30,
    )


def build_document_id(company: str, year: int, filename: str) -> str:
    """Stable id for one filing, used to replace chunks on re-upload."""
    stem = Path(filename).stem
    raw = f"{company}-{year}-{stem}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or "document"


def metadata_filter(*, company: str, year: int | None = None) -> Filter:
    """Qdrant payload filter. Year is included only when the caller set it.

    Chunk metadata is stored under the ``metadata`` payload key, so the filter
    must be a Qdrant ``Filter`` on ``metadata.company`` and ``metadata.year``.
    A plain dict is rejected by the current Qdrant client.
    """
    company_name = company.strip()
    if not company_name:
        raise ValueError("company is required")
    must = [
        FieldCondition(
            key="metadata.company",
            match=MatchValue(value=company_name),
        )
    ]
    if year is not None:
        must.append(
            FieldCondition(
                key="metadata.year",
                match=MatchValue(value=int(year)),
            )
        )
    return Filter(must=must)


def chunks_from_pdf(
    data: bytes,
    *,
    filename: str,
    company: str,
    year: int,
) -> list[Document]:
    """Split a PDF into chunks stamped with company, year, and document id.

    Args:
        data: Raw PDF bytes.
        filename: Original file name. Stored as ``source`` on each chunk.
        company: Company this filing belongs to. Matched exactly at retrieval.
        year: Filing year. Stored on every chunk so analyze can filter on it.

    Raises:
        ValueError: If the upload is empty, too large, not a PDF, has a bad
            year, or yields no text.
    """
    company_name = company.strip()
    if not company_name:
        raise ValueError("company is required")
    if year < 1900 or year > 2100:
        raise ValueError("year must be between 1900 and 2100")
    if not data:
        raise ValueError("PDF file is empty")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError(f"PDF exceeds the {MAX_PDF_BYTES} byte limit")

    safe_name = Path(filename).name
    if Path(safe_name).suffix.lower() != ".pdf":
        raise ValueError("Upload a .pdf file")
    if not data.startswith(b"%PDF"):
        raise ValueError("File content is not a PDF")

    document_id = build_document_id(company_name, year, safe_name)
    try:
        reader = PdfReader(BytesIO(data))
        documents = [
            Document(
                page_content=page.extract_text() or "",
                metadata={
                    "source": safe_name,
                    "page": page_number,
                    "company": company_name,
                    "year": year,
                    "document_id": document_id,
                },
            )
            for page_number, page in enumerate(reader.pages)
        ]
    except Exception as exc:  # noqa: BLE001 — surface loader/parse failures clearly
        raise ValueError(f"Failed to parse PDF '{safe_name}': {exc}") from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError(
            f"No text chunks produced from '{safe_name}'. "
            "Confirm the PDF is text-based (not a scanned image-only file)."
        )
    return chunks


def _ensure_payload_indexes(client: QdrantClient) -> None:
    """Index the fields retrieval filters on. Ignore indexes that already exist."""
    fields = (
        ("metadata.company", PayloadSchemaType.KEYWORD),
        ("metadata.document_id", PayloadSchemaType.KEYWORD),
        ("metadata.year", PayloadSchemaType.INTEGER),
    )
    for field_name, schema in fields:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=schema,
            )
        except Exception as exc:  # noqa: BLE001 — duplicate index is not a failure
            message = str(exc).lower()
            if "already exists" in message or "already exist" in message:
                continue
            logger.warning("Could not create payload index for %s: %s", field_name, exc)


def _delete_existing_document(client: QdrantClient, document_id: str) -> None:
    """Remove chunks from a previous upload of the same filing."""
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )


def _upsert_chunks(chunks: list[Document]) -> None:
    """Create the collection if needed, replace the same document, then upsert."""
    client = _qdrant_client()
    embeddings = _build_embeddings()
    api_key = _qdrant_api_key()
    document_id = str(chunks[0].metadata["document_id"])

    try:
        exists = client.collection_exists(collection_name=COLLECTION_NAME)
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to reach Qdrant at '{settings.QDRANT_URL}': {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown client/SDK errors
        raise ConnectionError(
            f"Unexpected error talking to Qdrant at '{settings.QDRANT_URL}': {exc}"
        ) from exc

    try:
        if not exists:
            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                url=settings.QDRANT_URL,
                api_key=api_key,
                collection_name=COLLECTION_NAME,
            )
        else:
            _delete_existing_document(client, document_id)
            vector_store = QdrantVectorStore.from_existing_collection(
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                url=settings.QDRANT_URL,
                api_key=api_key,
            )
            vector_store.add_documents(chunks)
        _ensure_payload_indexes(client)
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to upsert documents into Qdrant at '{settings.QDRANT_URL}' "
            f"(collection='{COLLECTION_NAME}'): {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown client/SDK errors
        raise ConnectionError(
            f"Unexpected error while writing to Qdrant collection "
            f"'{COLLECTION_NAME}': {exc}"
        ) from exc


def ingest_pdf_bytes(
    data: bytes,
    filename: str,
    *,
    company: str,
    year: int,
) -> IngestResponse:
    """Chunk, embed, and store an uploaded PDF.

    Re-uploading the same company, year, and filename replaces that filing's
    chunks instead of duplicating them.
    """
    chunks = chunks_from_pdf(data, filename=filename, company=company, year=year)
    _upsert_chunks(chunks)
    first = chunks[0].metadata
    logger.info(
        "Ingested %s chunks for '%s' year=%s document_id=%s into '%s'",
        len(chunks),
        first["company"],
        first["year"],
        first["document_id"],
        COLLECTION_NAME,
    )
    return IngestResponse(
        document_id=str(first["document_id"]),
        company=str(first["company"]),
        year=int(first["year"]),
        filename=str(first["source"]),
        chunk_count=len(chunks),
    )


def ingest_pdf(
    pdf_path: str = DEFAULT_PDF_PATH,
    *,
    company: str,
    year: int,
) -> IngestResponse:
    """Read a PDF from disk and ingest it. Prefer ``POST /api/v1/ingest``."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"PDF not found at '{pdf_path}'. "
            "Place a sample 10-K (or other report) there, or pass a valid path."
        )
    return ingest_pdf_bytes(path.read_bytes(), path.name, company=company, year=year)


def open_vector_store() -> QdrantVectorStore:
    """Connect to the existing ``financial_reports`` collection.

    Raises:
        ConnectionError: If Qdrant is unreachable or the collection does not
            exist yet (ingest a PDF first).
    """
    embeddings = _build_embeddings()
    api_key = _qdrant_api_key()
    try:
        return QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            url=settings.QDRANT_URL,
            api_key=api_key,
        )
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to connect to Qdrant collection '{COLLECTION_NAME}' at "
            f"'{settings.QDRANT_URL}'. Ensure Qdrant is running and that "
            f"POST /api/v1/ingest has created the collection. Underlying error: {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown client/SDK errors
        raise ConnectionError(
            f"Unexpected error opening Qdrant collection '{COLLECTION_NAME}': {exc}"
        ) from exc


def search_chunks(
    query: str,
    *,
    company: str,
    year: int | None = None,
    k: int = 4,
    vector_store: QdrantVectorStore | None = None,
) -> list[Document]:
    """Return the top ``k`` chunks for this company, and year when set.

    An empty list means nothing matched the filter. Callers treat that as a
    refusal rather than answering from another company's filing.
    """
    if k < 1:
        raise ValueError(f"k must be a positive integer, got {k}")
    store = vector_store or open_vector_store()
    return store.similarity_search(
        query,
        k=k,
        filter=metadata_filter(company=company, year=year),
    )


def get_retriever(k: int = 4, *, company: str, year: int | None = None):
    """Return a Qdrant retriever limited to ``company`` and optional ``year``."""
    if k < 1:
        raise ValueError(f"k must be a positive integer, got {k}")
    vector_store = open_vector_store()
    return vector_store.as_retriever(
        search_kwargs={
            "k": k,
            "filter": metadata_filter(company=company, year=year),
        }
    )

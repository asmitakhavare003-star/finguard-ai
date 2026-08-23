"""RAG vector storage helpers backed by Qdrant and OpenAI embeddings.

Provides PDF ingestion into a Qdrant collection and a similarity retriever for
downstream LangGraph / agent nodes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "financial_reports"
DEFAULT_PDF_PATH = "data/sample_10k.pdf"
EMBEDDING_MODEL = "text-embedding-3-small"


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


def ingest_pdf(pdf_path: str = DEFAULT_PDF_PATH) -> QdrantVectorStore:
    """Load a PDF, chunk it, embed it, and upsert chunks into Qdrant.

    Steps:
        1. Load pages with ``PyPDFLoader``.
        2. Split text with ``RecursiveCharacterTextSplitter``
           (chunk_size=1000, chunk_overlap=150).
        3. Embed chunks via ``OpenAIEmbeddings`` (``text-embedding-3-small``).
        4. Upsert into Qdrant collection ``financial_reports``.

    Args:
        pdf_path: Path to the PDF to ingest. Defaults to ``data/sample_10k.pdf``.

    Returns:
        The ``QdrantVectorStore`` instance backed by the upserted collection.

    Raises:
        FileNotFoundError: If ``pdf_path`` does not exist.
        ConnectionError: If Qdrant (or the embedding API path through the client)
            cannot be reached / rejects the request.
        ValueError: If the PDF loads but yields no usable text chunks.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"PDF not found at '{pdf_path}'. "
            "Place a sample 10-K (or other report) there, or pass a valid path."
        )

    try:
        loader = PyPDFLoader(str(path))
        documents = loader.load()
    except FileNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface loader/parse failures clearly
        raise RuntimeError(
            f"Failed to load or parse PDF '{pdf_path}': {exc}"
        ) from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError(
            f"No text chunks produced from '{pdf_path}'. "
            "Confirm the PDF is text-based (not a scanned image-only file)."
        )

    embeddings = _build_embeddings()
    api_key = _qdrant_api_key()

    try:
        vector_store = QdrantVectorStore.from_documents(
            documents=chunks,
            embedding=embeddings,
            url=settings.QDRANT_URL,
            api_key=api_key,
            collection_name=COLLECTION_NAME,
        )
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

    logger.info(
        "Ingested %s chunks from '%s' into Qdrant collection '%s'",
        len(chunks),
        pdf_path,
        COLLECTION_NAME,
    )
    return vector_store


def get_retriever(k: int = 4):
    """Return a Qdrant similarity retriever over ``financial_reports``.

    Connects to the existing Qdrant collection configured via settings and
    returns a LangChain retriever that fetches the top ``k`` chunks.

    Args:
        k: Number of nearest-neighbor chunks to return per query.

    Returns:
        A LangChain ``VectorStoreRetriever`` bound to the Qdrant collection.

    Raises:
        ConnectionError: If Qdrant is unreachable or the collection cannot be
            opened (e.g. it was never created — run ``ingest_pdf`` first).
        ValueError: If ``k`` is not a positive integer.
    """
    if k < 1:
        raise ValueError(f"k must be a positive integer, got {k}")

    embeddings = _build_embeddings()
    api_key = _qdrant_api_key()

    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            url=settings.QDRANT_URL,
            api_key=api_key,
        )
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to connect to Qdrant collection '{COLLECTION_NAME}' at "
            f"'{settings.QDRANT_URL}'. Ensure Qdrant is running and that "
            f"ingest_pdf() has created the collection. Underlying error: {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown client/SDK errors
        raise ConnectionError(
            f"Unexpected error opening Qdrant collection '{COLLECTION_NAME}': {exc}"
        ) from exc

    return vector_store.as_retriever(search_kwargs={"k": k})

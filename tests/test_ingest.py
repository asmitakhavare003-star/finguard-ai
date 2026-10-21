"""Tests for PDF ingest metadata and the upload API. No live Qdrant required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.schemas.financial import IngestResponse
from app.services.vector_store import (
    build_document_id,
    chunks_from_pdf,
    metadata_filter,
)


class _Page:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _Reader:
    def __init__(self, _stream: object) -> None:
        self.pages = [
            _Page("Net sales were 391,035 million."),
            _Page("Net income was 93,736 million."),
        ]


def test_document_id_is_stable_slug() -> None:
    assert (
        build_document_id("Apple Inc.", 2024, "sample_10k.pdf")
        == "apple-inc-2024-sample-10k"
    )


def test_metadata_filter_includes_year_only_when_set() -> None:
    company_only = metadata_filter(company=" Apple Inc. ")
    assert company_only.must is not None
    assert len(company_only.must) == 1
    assert company_only.must[0].key == "metadata.company"
    assert company_only.must[0].match.value == "Apple Inc."

    with_year = metadata_filter(company="Apple Inc.", year=2024)
    assert with_year.must is not None
    assert [condition.key for condition in with_year.must] == [
        "metadata.company",
        "metadata.year",
    ]
    assert with_year.must[1].match.value == 2024


def test_chunks_carry_company_and_year(monkeypatch) -> None:
    monkeypatch.setattr("app.services.vector_store.PdfReader", _Reader)
    chunks = chunks_from_pdf(
        b"%PDF-1.4 fake",
        filename="sample_10k.pdf",
        company="Apple Inc.",
        year=2024,
    )
    assert chunks
    assert chunks[0].metadata["company"] == "Apple Inc."
    assert chunks[0].metadata["year"] == 2024
    assert chunks[0].metadata["document_id"] == "apple-inc-2024-sample-10k"
    assert chunks[0].metadata["source"] == "sample_10k.pdf"


def test_chunks_reject_non_pdf() -> None:
    with pytest.raises(ValueError, match="pdf"):
        chunks_from_pdf(
            b"not a pdf",
            filename="notes.txt",
            company="Apple Inc.",
            year=2024,
        )


def test_ingest_endpoint_returns_chunk_count(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_ingest(data: bytes, filename: str, *, company: str, year: int) -> IngestResponse:
        assert data.startswith(b"%PDF")
        assert filename == "sample_10k.pdf"
        assert company == "Apple Inc."
        assert year == 2024
        return IngestResponse(
            document_id="apple-inc-2024-sample-10k",
            company=company,
            year=year,
            filename=filename,
            chunk_count=12,
        )

    monkeypatch.setattr("app.main.ingest_pdf_bytes", fake_ingest)
    response = client.post(
        "/api/v1/ingest",
        files={"file": ("sample_10k.pdf", b"%PDF-1.4\n", "application/pdf")},
        data={"company": "Apple Inc.", "year": "2024"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] == 12
    assert body["company"] == "Apple Inc."
    assert body["year"] == 2024
    assert body["document_id"] == "apple-inc-2024-sample-10k"


def test_ingest_endpoint_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ingest",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"company": "Apple Inc.", "year": "2024"},
    )
    assert response.status_code == 400

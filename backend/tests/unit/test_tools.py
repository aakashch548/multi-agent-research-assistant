"""Unit tests for research tools."""

from __future__ import annotations

import pytest

from backend.tools.citation_extractor import CitationExtractor
from backend.tools.diagram_generator import DiagramGenerator
from backend.tools.export import ReportExporter


class TestCitationExtractor:
    def test_extract_citations(self) -> None:
        extractor = CitationExtractor()
        sources = [
            {"url": "https://example.com/1", "title": "Source 1", "content": "AI content"},
            {"url": "https://example.com/2", "title": "Source 2", "content": "ML content"},
        ]
        text = "AI is transforming the world."
        citations = extractor.extract_citations(text, sources)

        assert len(citations) == 2
        assert citations[0].source_url == "https://example.com/1"

    def test_format_citations_apa(self) -> None:
        extractor = CitationExtractor()
        sources = [
            {"url": "https://example.com/1", "title": "AI Report", "content": "Content"},
        ]
        citations = extractor.extract_citations("text", sources)
        formatted = extractor.format_citations_apa(citations)

        assert "AI Report" in formatted
        assert "https://example.com/1" in formatted


class TestDiagramGenerator:
    def test_generate_workflow_diagram(self) -> None:
        gen = DiagramGenerator()
        steps = [
            {"name": "Planning", "description": "Decompose query"},
            {"name": "Research", "description": "Search and retrieve"},
            {"name": "Verify", "description": "Fact check"},
        ]
        diagram = gen.generate_workflow_diagram(steps)

        assert "graph" in diagram.lower() or "flowchart" in diagram.lower()
        assert "Planning" in diagram

    def test_generate_concept_map(self) -> None:
        gen = DiagramGenerator()
        concepts = [
            {"name": "AI", "connections": ["Machine Learning", "Deep Learning"]},
            {"name": "Machine Learning", "connections": ["Supervised", "Unsupervised"]},
        ]
        diagram = gen.generate_concept_map(concepts)

        assert "AI" in diagram
        assert "Machine Learning" in diagram


class TestReportExporter:
    def test_export_markdown(self) -> None:
        exporter = ReportExporter()
        report = "# Test Report\n\nThis is a test."
        citations = [{"text": "citation", "source_url": "https://example.com"}]
        metadata = {"duration_ms": 1234}

        result = exporter.export_markdown(report, citations, metadata)

        assert "# Test Report" in result
        assert "https://example.com" in result

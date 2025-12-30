"""
Parser Agent - Extract structured content from scientific papers

This agent is responsible for parsing PDF files and extracting
structured information including text, sections, equations, and code snippets.
"""

from pathlib import Path
from typing import Optional

from ..models.paper import Paper, Section, Algorithm
from ..tools.pdf_parser import PDFParser


class ParserAgent:
    """
    Agent for parsing scientific papers into structured format.

    This agent handles the first stage of the Paper2Code pipeline,
    converting raw PDF files into structured Paper objects.

    Attributes:
        pdf_parser: PDF parsing tool instance

    Example:
        >>> agent = ParserAgent()
        >>> paper = agent.parse("path/to/paper.pdf")
        >>> print(paper.title)
    """

    def __init__(self):
        """Initialize the Parser Agent."""
        self.pdf_parser = PDFParser()

    def parse(self, pdf_path: str | Path) -> Paper:
        """
        Parse a PDF file and return structured Paper object.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Paper object containing structured content

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF parsing fails
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise ValueError(f"Expected PDF file, got: {pdf_path.suffix}")

        try:
            paper = self.pdf_parser.parse(pdf_path)
            return paper
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}") from e

    def parse_to_dict(self, pdf_path: str | Path) -> dict:
        """
        Parse PDF and return as dictionary for JSON serialization.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing paper content

        Example:
            >>> agent = ParserAgent()
            >>> data = agent.parse_to_dict("paper.pdf")
            >>> json.dumps(data)
        """
        paper = self.parse(pdf_path)
        return self._paper_to_dict(paper)

    def _paper_to_dict(self, paper: Paper) -> dict:
        """Convert Paper object to dictionary."""
        return {
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "level": s.level,
                    "subsections": [
                        {
                            "title": sub.title,
                            "content": sub.content,
                            "level": sub.level,
                        }
                        for sub in (s.subsections or [])
                    ],
                }
                for s in paper.sections
            ],
            "equations": paper.equations,
            "code_snippets": paper.code_snippets,
            "algorithms": [
                {
                    "name": a.name,
                    "description": a.description,
                    "pseudocode": a.pseudocode,
                    "inputs": a.inputs,
                    "outputs": a.outputs,
                }
                for a in (paper.algorithms or [])
            ],
            "references": paper.references,
            "page_count": paper.page_count,
            "source_path": paper.source_path,
        }

    def extract_method_section(self, paper: Paper) -> Optional[str]:
        """
        Extract the methodology/algorithm section content.

        This is typically the most important section for code generation.

        Args:
            paper: Parsed Paper object

        Returns:
            Content of method section if found, None otherwise
        """
        method_keywords = [
            "method",
            "methodology",
            "approach",
            "algorithm",
            "proposed",
            "model",
            "architecture",
        ]

        for section in paper.sections:
            section_title_lower = section.title.lower()
            for keyword in method_keywords:
                if keyword in section_title_lower:
                    return section.content

        return None

    def extract_algorithm_blocks(self, paper: Paper) -> list[str]:
        """
        Extract all algorithm/pseudocode blocks from paper.

        Args:
            paper: Parsed Paper object

        Returns:
            List of algorithm/pseudocode strings
        """
        algorithms = []

        # Check existing algorithms
        if paper.algorithms:
            for algo in paper.algorithms:
                if algo.pseudocode:
                    algorithms.append(algo.pseudocode)

        # Also check code snippets that might be algorithms
        if paper.code_snippets:
            algorithms.extend(paper.code_snippets)

        return algorithms

    def get_summary(self, paper: Paper) -> dict:
        """
        Generate a summary of the parsed paper.

        Args:
            paper: Parsed Paper object

        Returns:
            Dictionary with summary statistics
        """
        return {
            "title": paper.title,
            "authors_count": len(paper.authors),
            "abstract_length": len(paper.abstract) if paper.abstract else 0,
            "section_count": len(paper.sections),
            "equation_count": len(paper.equations) if paper.equations else 0,
            "code_snippet_count": len(paper.code_snippets) if paper.code_snippets else 0,
            "algorithm_count": len(paper.algorithms) if paper.algorithms else 0,
            "page_count": paper.page_count,
            "sections": [s.title for s in paper.sections],
        }

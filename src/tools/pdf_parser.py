"""
PDF Parser Tool - Extract text and structure from scientific papers
"""

import re
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from ..models.paper import Paper, Section


class PDFParser:
    """Parse PDF files and extract structured content"""

    # Common section titles in scientific papers
    SECTION_PATTERNS = [
        r"^(?:\d+\.?\s*)?(abstract)$",
        r"^(?:\d+\.?\s*)?(introduction)$",
        r"^(?:\d+\.?\s*)?(related\s+work|background|literature\s+review)$",
        r"^(?:\d+\.?\s*)?(method|methodology|approach|algorithm|proposed\s+method)s?$",
        r"^(?:\d+\.?\s*)?(experiment|evaluation|result)s?$",
        r"^(?:\d+\.?\s*)?(discussion)$",
        r"^(?:\d+\.?\s*)?(conclusion)s?$",
        r"^(?:\d+\.?\s*)?(reference|bibliography)s?$",
        r"^(?:\d+\.?\s*)?(appendix|appendices)$",
    ]

    # Pattern for detecting equations
    EQUATION_PATTERNS = [
        r"\$[^\$]+\$",  # Inline LaTeX
        r"\\\[[^\]]+\\\]",  # Display LaTeX
        r"\\begin\{equation\}.*?\\end\{equation\}",
        r"\\begin\{align\}.*?\\end\{align\}",
    ]

    # Pattern for detecting code blocks
    CODE_PATTERNS = [
        r"```[\s\S]*?```",
        r"(?:def|class|import|from|if|for|while)\s+\w+",
    ]

    def __init__(self):
        self.current_doc: Optional[fitz.Document] = None

    def parse(self, pdf_path: str | Path) -> Paper:
        """
        Parse a PDF file and return structured Paper object

        Args:
            pdf_path: Path to PDF file

        Returns:
            Paper object with extracted content
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.current_doc = fitz.open(pdf_path)

        try:
            # Extract basic metadata
            metadata = self._extract_metadata()

            # Extract full text
            full_text = self._extract_full_text()

            # Parse sections
            sections = self._parse_sections(full_text)

            # Extract equations
            equations = self._extract_equations(full_text)

            # Extract code snippets
            code_snippets = self._extract_code_snippets(full_text)

            # Build Paper object
            paper = Paper(
                title=metadata.get("title", "Untitled"),
                authors=metadata.get("authors", []),
                abstract=self._extract_abstract(full_text),
                sections=sections,
                full_text=full_text,
                equations=equations,
                code_snippets=code_snippets,
                source_path=str(pdf_path),
                page_count=len(self.current_doc),
            )

            return paper

        finally:
            self.current_doc.close()
            self.current_doc = None

    def _extract_metadata(self) -> dict:
        """Extract document metadata"""
        if not self.current_doc:
            return {}

        metadata = self.current_doc.metadata
        result = {
            "title": metadata.get("title", ""),
            "authors": [],
            "year": None,
        }

        # Try to extract title from first page if not in metadata
        if not result["title"]:
            first_page = self.current_doc[0]
            blocks = first_page.get_text("blocks")
            if blocks:
                # Usually the title is the first large text block
                for block in blocks[:5]:
                    if len(block[4]) > 10:  # Skip very short text
                        result["title"] = block[4].strip().replace("\n", " ")
                        break

        # Extract author from metadata
        if metadata.get("author"):
            result["authors"] = [
                a.strip() for a in metadata["author"].split(",") if a.strip()
            ]

        return result

    def _extract_full_text(self) -> str:
        """Extract all text from PDF"""
        if not self.current_doc:
            return ""

        full_text = []
        for page in self.current_doc:
            text = page.get_text("text")
            full_text.append(text)

        return "\n\n".join(full_text)

    def _extract_abstract(self, full_text: str) -> str:
        """Extract abstract section"""
        # Try to find abstract section
        abstract_pattern = r"(?i)abstract\s*\n+(.*?)(?=\n\s*(?:\d+\.?\s*)?(?:introduction|keywords|1\.))"
        match = re.search(abstract_pattern, full_text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: take first paragraph after title
        paragraphs = full_text.split("\n\n")
        for p in paragraphs[1:5]:  # Skip title, check next few
            if len(p) > 200:  # Abstract is usually substantial
                return p.strip()

        return ""

    def _parse_sections(self, full_text: str) -> list[Section]:
        """Parse text into sections"""
        sections = []
        current_section = None
        current_content = []

        lines = full_text.split("\n")

        for line in lines:
            line_stripped = line.strip()

            # Check if this line is a section header
            is_header = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line_stripped.lower()):
                    is_header = True
                    break

            # Also check for numbered sections like "1. Introduction"
            if re.match(r"^\d+\.?\s+[A-Z]", line_stripped):
                is_header = True

            if is_header:
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                current_section = Section(
                    title=line_stripped,
                    content="",
                    level=1,
                )
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_equations(self, full_text: str) -> list[str]:
        """Extract mathematical equations"""
        equations = []
        for pattern in self.EQUATION_PATTERNS:
            matches = re.findall(pattern, full_text, re.DOTALL)
            equations.extend(matches)
        return list(set(equations))  # Remove duplicates

    def _extract_code_snippets(self, full_text: str) -> list[str]:
        """Extract code snippets from text"""
        snippets = []

        # Look for markdown code blocks
        code_block_pattern = r"```(?:\w+)?\n([\s\S]*?)```"
        matches = re.findall(code_block_pattern, full_text)
        snippets.extend(matches)

        # Look for Algorithm/Pseudocode blocks
        algo_pattern = r"(?:Algorithm|Procedure|Function)\s+\d*:?\s*([\s\S]*?)(?=\n\s*\n|\Z)"
        matches = re.findall(algo_pattern, full_text, re.IGNORECASE)
        snippets.extend(matches)

        return snippets

    def get_page_text(self, page_num: int) -> str:
        """Get text from a specific page"""
        if not self.current_doc or page_num >= len(self.current_doc):
            return ""
        return self.current_doc[page_num].get_text("text")

    def get_page_count(self) -> int:
        """Get total page count"""
        return len(self.current_doc) if self.current_doc else 0


# Convenience function
def parse_pdf(pdf_path: str | Path) -> Paper:
    """Parse a PDF file and return Paper object"""
    parser = PDFParser()
    return parser.parse(pdf_path)

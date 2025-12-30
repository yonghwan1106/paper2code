"""
Paper Data Models - Represents parsed scientific paper structure
"""

from typing import Optional
from pydantic import BaseModel, Field


class Section(BaseModel):
    """Represents a section of a paper"""

    title: str = Field(description="Section title")
    content: str = Field(description="Section text content")
    level: int = Field(default=1, description="Heading level (1=H1, 2=H2, etc.)")
    subsections: list["Section"] = Field(default_factory=list)


class Algorithm(BaseModel):
    """Represents an algorithm extracted from a paper"""

    name: str = Field(description="Algorithm name or identifier")
    description: str = Field(description="Brief description of what the algorithm does")
    pseudocode: Optional[str] = Field(default=None, description="Pseudocode if available")
    inputs: list[dict] = Field(
        default_factory=list,
        description="List of inputs with name, type, description",
    )
    outputs: list[dict] = Field(
        default_factory=list,
        description="List of outputs with name, type, description",
    )
    steps: list[str] = Field(default_factory=list, description="Algorithm steps in order")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required libraries (numpy, torch, etc.)",
    )
    hyperparameters: list[dict] = Field(
        default_factory=list,
        description="Tunable parameters with name, default, description",
    )
    equations: list[str] = Field(
        default_factory=list,
        description="Mathematical equations in LaTeX format",
    )
    complexity: Optional[str] = Field(
        default=None,
        description="Time/space complexity if mentioned",
    )


class Paper(BaseModel):
    """Represents a parsed scientific paper"""

    # Metadata
    title: str = Field(description="Paper title")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    abstract: str = Field(default="", description="Paper abstract")
    year: Optional[int] = Field(default=None, description="Publication year")
    source: Optional[str] = Field(default=None, description="Journal/Conference name")
    doi: Optional[str] = Field(default=None, description="DOI if available")

    # Content
    sections: list[Section] = Field(default_factory=list, description="Paper sections")
    full_text: str = Field(default="", description="Full paper text content")

    # Extracted elements
    algorithms: list[Algorithm] = Field(
        default_factory=list,
        description="Extracted algorithms",
    )
    equations: list[str] = Field(
        default_factory=list,
        description="Mathematical equations found",
    )
    code_snippets: list[str] = Field(
        default_factory=list,
        description="Code snippets in the paper",
    )
    tables: list[dict] = Field(
        default_factory=list,
        description="Tables data",
    )
    figures: list[dict] = Field(
        default_factory=list,
        description="Figure references and captions",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Bibliography references",
    )

    # Processing metadata
    source_path: Optional[str] = Field(default=None, description="Original PDF path")
    page_count: int = Field(default=0, description="Number of pages")
    parse_quality: float = Field(
        default=1.0,
        description="Estimated parse quality (0-1)",
    )

    def get_method_section(self) -> Optional[Section]:
        """Get the methodology/methods section if exists"""
        method_keywords = ["method", "approach", "algorithm", "implementation"]
        for section in self.sections:
            if any(kw in section.title.lower() for kw in method_keywords):
                return section
        return None

    def get_main_algorithm(self) -> Optional[Algorithm]:
        """Get the primary algorithm if multiple exist"""
        if self.algorithms:
            return self.algorithms[0]
        return None

    def to_context_string(self) -> str:
        """Convert paper to a context string for LLM"""
        parts = [
            f"# {self.title}",
            "",
            f"## Abstract",
            self.abstract,
            "",
        ]

        for section in self.sections:
            parts.append(f"## {section.title}")
            parts.append(section.content)
            parts.append("")

        if self.algorithms:
            parts.append("## Extracted Algorithms")
            for alg in self.algorithms:
                parts.append(f"### {alg.name}")
                parts.append(alg.description)
                if alg.pseudocode:
                    parts.append(f"```\n{alg.pseudocode}\n```")
                parts.append("")

        return "\n".join(parts)

"""
Analyzer Agent - Extract and analyze algorithms from scientific papers

This agent analyzes parsed paper content and extracts detailed
algorithm specifications that can be used for code generation.
"""

import json
from typing import Optional

from ..models.paper import Paper, Algorithm
from ..tools.llm_client import LLMClient


class AnalyzerAgent:
    """
    Agent for analyzing papers and extracting algorithm specifications.

    This agent uses LLM to understand paper content and extract
    structured algorithm specifications including inputs, outputs,
    steps, and dependencies.

    Attributes:
        llm_client: LLM client for analysis
        max_context_length: Maximum context length for LLM

    Example:
        >>> agent = AnalyzerAgent()
        >>> spec = agent.analyze(paper)
        >>> print(spec["algorithms"][0]["name"])
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the Analyzer Agent.

        Args:
            llm_client: Optional LLM client instance
        """
        self.llm_client = llm_client or LLMClient()
        self.max_context_length = 100000  # Claude context window

    def analyze(self, paper: Paper) -> dict:
        """
        Analyze paper and extract algorithm specifications.

        Args:
            paper: Parsed Paper object

        Returns:
            Dictionary containing algorithm specifications

        Example:
            >>> spec = agent.analyze(paper)
            >>> print(spec["algorithms"])
        """
        # Prepare paper content for analysis
        paper_content = self._prepare_content(paper)

        # Use LLM to analyze algorithms
        result = self.llm_client.analyze_algorithm(paper_content)

        # Validate and enhance result
        result = self._validate_result(result)

        return result

    def analyze_from_dict(self, paper_dict: dict) -> dict:
        """
        Analyze paper from dictionary representation.

        Args:
            paper_dict: Dictionary containing paper content

        Returns:
            Algorithm specifications
        """
        # Prepare content string from dictionary
        content_parts = []

        if paper_dict.get("title"):
            content_parts.append(f"Title: {paper_dict['title']}")

        if paper_dict.get("abstract"):
            content_parts.append(f"\nAbstract:\n{paper_dict['abstract']}")

        if paper_dict.get("sections"):
            for section in paper_dict["sections"]:
                content_parts.append(f"\n## {section['title']}\n{section['content']}")

        if paper_dict.get("equations"):
            content_parts.append(f"\nEquations:\n" + "\n".join(paper_dict["equations"]))

        if paper_dict.get("code_snippets"):
            content_parts.append(f"\nCode Snippets:\n" + "\n---\n".join(paper_dict["code_snippets"]))

        paper_content = "\n".join(content_parts)

        # Truncate if too long
        if len(paper_content) > self.max_context_length:
            paper_content = paper_content[:self.max_context_length]

        result = self.llm_client.analyze_algorithm(paper_content)
        return self._validate_result(result)

    def _prepare_content(self, paper: Paper) -> str:
        """
        Prepare paper content for LLM analysis.

        Args:
            paper: Paper object

        Returns:
            Formatted string for analysis
        """
        content_parts = []

        # Title
        content_parts.append(f"Title: {paper.title}")

        # Authors
        if paper.authors:
            content_parts.append(f"Authors: {', '.join(paper.authors)}")

        # Abstract
        if paper.abstract:
            content_parts.append(f"\nAbstract:\n{paper.abstract}")

        # Sections (prioritize method/algorithm sections)
        method_section = None
        other_sections = []

        for section in paper.sections:
            section_text = f"\n## {section.title}\n{section.content}"

            # Check if this is a method/algorithm section
            title_lower = section.title.lower()
            if any(kw in title_lower for kw in ["method", "algorithm", "approach", "model"]):
                method_section = section_text
            else:
                other_sections.append(section_text)

        # Add method section first (most important)
        if method_section:
            content_parts.append("\n--- METHODOLOGY SECTION (Primary) ---")
            content_parts.append(method_section)

        # Add other sections
        for section_text in other_sections:
            content_parts.append(section_text)

        # Equations
        if paper.equations:
            content_parts.append("\n--- EQUATIONS ---")
            for i, eq in enumerate(paper.equations, 1):
                content_parts.append(f"Equation {i}: {eq}")

        # Code snippets / Pseudocode
        if paper.code_snippets:
            content_parts.append("\n--- CODE/PSEUDOCODE ---")
            for i, snippet in enumerate(paper.code_snippets, 1):
                content_parts.append(f"Snippet {i}:\n{snippet}")

        # Existing algorithms
        if paper.algorithms:
            content_parts.append("\n--- ALGORITHMS ---")
            for algo in paper.algorithms:
                content_parts.append(f"Algorithm: {algo.name}")
                if algo.description:
                    content_parts.append(f"Description: {algo.description}")
                if algo.pseudocode:
                    content_parts.append(f"Pseudocode:\n{algo.pseudocode}")

        full_content = "\n".join(content_parts)

        # Truncate if exceeds context limit
        if len(full_content) > self.max_context_length:
            full_content = full_content[:self.max_context_length]
            full_content += "\n\n[Content truncated due to length]"

        return full_content

    def _validate_result(self, result: dict) -> dict:
        """
        Validate and clean up analysis result.

        Args:
            result: Raw analysis result

        Returns:
            Validated result dictionary
        """
        # Check for parse error
        if result.get("parse_error"):
            return {
                "algorithms": [],
                "main_algorithm_index": 0,
                "paper_domain": "unknown",
                "implementation_notes": "Failed to parse LLM response",
                "raw_response": result.get("raw_response", ""),
                "error": True,
            }

        # Ensure required fields exist
        if "algorithms" not in result:
            result["algorithms"] = []

        if "main_algorithm_index" not in result:
            result["main_algorithm_index"] = 0

        if "paper_domain" not in result:
            result["paper_domain"] = "unknown"

        # Validate each algorithm
        for algo in result["algorithms"]:
            # Ensure required fields
            algo.setdefault("name", "Unnamed Algorithm")
            algo.setdefault("description", "")
            algo.setdefault("purpose", "")
            algo.setdefault("inputs", [])
            algo.setdefault("outputs", [])
            algo.setdefault("steps", [])
            algo.setdefault("dependencies", [])
            algo.setdefault("hyperparameters", [])

            # Validate inputs
            for inp in algo["inputs"]:
                inp.setdefault("name", "input")
                inp.setdefault("type", "Any")
                inp.setdefault("description", "")

            # Validate outputs
            for out in algo["outputs"]:
                out.setdefault("name", "output")
                out.setdefault("type", "Any")
                out.setdefault("description", "")

            # Validate hyperparameters
            for param in algo["hyperparameters"]:
                param.setdefault("name", "param")
                param.setdefault("type", "float")
                param.setdefault("default", None)
                param.setdefault("description", "")

        return result

    def get_main_algorithm(self, analysis_result: dict) -> Optional[dict]:
        """
        Get the main algorithm from analysis result.

        Args:
            analysis_result: Result from analyze()

        Returns:
            Main algorithm specification or None
        """
        algorithms = analysis_result.get("algorithms", [])
        if not algorithms:
            return None

        main_index = analysis_result.get("main_algorithm_index", 0)
        if main_index < len(algorithms):
            return algorithms[main_index]

        return algorithms[0] if algorithms else None

    def get_dependencies(self, analysis_result: dict) -> list[str]:
        """
        Get all unique dependencies from analysis.

        Args:
            analysis_result: Result from analyze()

        Returns:
            List of unique dependency names
        """
        deps = set()

        for algo in analysis_result.get("algorithms", []):
            for dep in algo.get("dependencies", []):
                deps.add(dep.lower())

        return sorted(list(deps))

    def summarize_analysis(self, analysis_result: dict) -> str:
        """
        Generate human-readable summary of analysis.

        Args:
            analysis_result: Result from analyze()

        Returns:
            Summary string
        """
        algorithms = analysis_result.get("algorithms", [])
        domain = analysis_result.get("paper_domain", "unknown")

        summary_parts = [
            f"Domain: {domain}",
            f"Algorithms found: {len(algorithms)}",
        ]

        for i, algo in enumerate(algorithms):
            is_main = i == analysis_result.get("main_algorithm_index", 0)
            main_marker = " (MAIN)" if is_main else ""
            summary_parts.append(f"\n{i+1}. {algo['name']}{main_marker}")
            summary_parts.append(f"   Purpose: {algo.get('purpose', 'N/A')}")
            summary_parts.append(f"   Inputs: {len(algo.get('inputs', []))}")
            summary_parts.append(f"   Outputs: {len(algo.get('outputs', []))}")
            summary_parts.append(f"   Steps: {len(algo.get('steps', []))}")
            summary_parts.append(f"   Dependencies: {', '.join(algo.get('dependencies', []))}")

        notes = analysis_result.get("implementation_notes", "")
        if notes:
            summary_parts.append(f"\nNotes: {notes}")

        return "\n".join(summary_parts)

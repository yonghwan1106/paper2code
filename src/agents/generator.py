"""
Generator Agent - Generate Python code from algorithm specifications

This agent generates executable Python code based on analyzed
algorithm specifications from scientific papers.
"""

import json
from datetime import datetime
from typing import Optional

from ..models.code_project import CodeProject, CodeFile, CodeDesign
from ..tools.llm_client import LLMClient


class GeneratorAgent:
    """
    Agent for generating Python code from algorithm specifications.

    This agent uses LLM to generate production-quality Python code
    that implements the algorithms described in scientific papers.

    Attributes:
        llm_client: LLM client for code generation

    Example:
        >>> agent = GeneratorAgent()
        >>> project = agent.generate(algorithm_spec, paper_context)
        >>> project.save_to_directory("./output")
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the Generator Agent.

        Args:
            llm_client: Optional LLM client instance
        """
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        algorithm_spec: dict,
        paper_context: str = "",
    ) -> CodeProject:
        """
        Generate Python code project from algorithm specification.

        Args:
            algorithm_spec: Algorithm specification from Analyzer
            paper_context: Additional context from the paper

        Returns:
            CodeProject containing generated files

        Raises:
            ValueError: If code generation fails
        """
        # Get main algorithm if multiple exist
        main_algo = self._get_main_algorithm(algorithm_spec)

        if not main_algo:
            raise ValueError("No algorithm found in specification")

        # Generate code using LLM
        result = self.llm_client.generate_code(main_algo, paper_context)

        # Check for errors
        if result.get("parse_error"):
            raise ValueError(f"Failed to generate code: {result.get('raw_response', 'Unknown error')}")

        # Build CodeProject
        project = self._build_project(result, main_algo)

        return project

    def generate_from_analysis(
        self,
        analysis_result: dict,
        paper_content: str = "",
    ) -> CodeProject:
        """
        Generate code project from full analysis result.

        Args:
            analysis_result: Result from AnalyzerAgent.analyze()
            paper_content: Original paper content for context

        Returns:
            CodeProject with generated code
        """
        # Extract main algorithm
        algorithms = analysis_result.get("algorithms", [])
        if not algorithms:
            raise ValueError("No algorithms found in analysis result")

        main_index = analysis_result.get("main_algorithm_index", 0)
        main_algo = algorithms[min(main_index, len(algorithms) - 1)]

        # Generate with context
        result = self.llm_client.generate_code(
            main_algo,
            paper_content[:5000] if paper_content else "",
        )

        if result.get("parse_error"):
            raise ValueError(f"Failed to generate code: {result.get('raw_response', 'Unknown error')}")

        project = self._build_project(result, main_algo)

        # Add domain info
        project.domain = analysis_result.get("paper_domain", "unknown")

        return project

    def _get_main_algorithm(self, spec: dict) -> Optional[dict]:
        """Extract main algorithm from specification."""
        algorithms = spec.get("algorithms", [])
        if not algorithms:
            # Maybe spec is already a single algorithm
            if "name" in spec and "steps" in spec:
                return spec
            return None

        main_index = spec.get("main_algorithm_index", 0)
        if main_index < len(algorithms):
            return algorithms[main_index]

        return algorithms[0]

    def _build_project(self, generation_result: dict, algorithm: dict) -> CodeProject:
        """
        Build CodeProject from generation result.

        Args:
            generation_result: LLM generation result
            algorithm: Algorithm specification

        Returns:
            CodeProject instance
        """
        files = []

        for file_data in generation_result.get("files", []):
            code_file = CodeFile(
                filename=file_data.get("filename", "untitled.py"),
                path=file_data.get("path", file_data.get("filename", "untitled.py")),
                content=file_data.get("content", ""),
                description=file_data.get("description", ""),
                is_entrypoint=file_data.get("is_entrypoint", False),
            )
            files.append(code_file)

        # Ensure we have at least main.py if no entrypoint
        has_entrypoint = any(f.is_entrypoint for f in files)
        if not has_entrypoint and files:
            # Mark first file as entrypoint
            for f in files:
                if f.filename in ["main.py", "demo.py", "run.py"]:
                    f.is_entrypoint = True
                    has_entrypoint = True
                    break

            if not has_entrypoint:
                files[0].is_entrypoint = True

        # Build requirements list
        requirements = generation_result.get("requirements", [])
        if not requirements:
            # Use algorithm dependencies as fallback
            requirements = algorithm.get("dependencies", [])

        # Format requirements properly
        formatted_requirements = []
        for req in requirements:
            if ">=" in req or "==" in req or "<" in req:
                formatted_requirements.append(req)
            else:
                formatted_requirements.append(req)

        # Create project
        project = CodeProject(
            name=self._sanitize_name(algorithm.get("name", "generated_algorithm")),
            description=algorithm.get("description", ""),
            files=files,
            requirements=formatted_requirements,
            python_version=generation_result.get("python_version", "3.11"),
            usage=generation_result.get("usage", "python main.py"),
            notes=generation_result.get("notes", ""),
        )

        return project

    def _sanitize_name(self, name: str) -> str:
        """
        Convert algorithm name to valid Python module name.

        Args:
            name: Original algorithm name

        Returns:
            Sanitized name suitable for module/directory name
        """
        # Replace spaces and special characters
        sanitized = name.lower()
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace("-", "_")

        # Remove invalid characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")

        # Ensure doesn't start with number
        if sanitized and sanitized[0].isdigit():
            sanitized = "algo_" + sanitized

        return sanitized or "generated_algorithm"

    def refine_code(
        self,
        project: CodeProject,
        feedback: str,
    ) -> CodeProject:
        """
        Refine generated code based on feedback.

        Args:
            project: Existing CodeProject
            feedback: Feedback for improvement

        Returns:
            Refined CodeProject
        """
        # Get main file content
        main_file = project.get_entrypoint()
        if not main_file:
            main_file = project.files[0] if project.files else None

        if not main_file:
            return project

        # Prepare all code for refinement
        all_code = "\n\n".join([
            f"# File: {f.filename}\n{f.content}"
            for f in project.files
        ])

        # Use LLM to refine
        prompt = f"""Refine the following Python code based on the feedback.

Current Code:
```python
{all_code}
```

Feedback:
{feedback}

Provide the complete refined code for all files in the same JSON format as before.
"""

        result = self.llm_client.complete(prompt)

        try:
            # Parse JSON from response
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0]
            else:
                json_str = result

            refined = json.loads(json_str.strip())

            # Build new project from refined result
            new_files = []
            for file_data in refined.get("files", []):
                new_files.append(CodeFile(
                    filename=file_data.get("filename"),
                    path=file_data.get("path", file_data.get("filename")),
                    content=file_data.get("content", ""),
                    description=file_data.get("description", ""),
                    is_entrypoint=file_data.get("is_entrypoint", False),
                ))

            if new_files:
                project.files = new_files

            if refined.get("requirements"):
                project.requirements = refined["requirements"]

        except (json.JSONDecodeError, KeyError):
            # If parsing fails, return original project
            pass

        return project

    def generate_tests(self, project: CodeProject) -> CodeFile:
        """
        Generate test file for the project.

        Args:
            project: CodeProject to generate tests for

        Returns:
            CodeFile containing test code
        """
        # Get all code
        all_code = "\n\n".join([
            f"# File: {f.filename}\n{f.content}"
            for f in project.files
        ])

        prompt = f"""Generate pytest unit tests for the following Python code.

Code:
```python
{all_code}
```

Generate comprehensive tests that:
1. Test main functions/classes
2. Test edge cases
3. Use meaningful assertions
4. Follow pytest conventions

Return only the Python test code, no JSON wrapper."""

        test_code = self.llm_client.complete(prompt)

        # Clean up response
        if "```python" in test_code:
            test_code = test_code.split("```python")[1].split("```")[0]
        elif "```" in test_code:
            test_code = test_code.split("```")[1].split("```")[0]

        return CodeFile(
            filename="test_algorithm.py",
            path="tests/test_algorithm.py",
            content=test_code.strip(),
            description="Unit tests for the algorithm implementation",
            is_entrypoint=False,
        )

    def get_generation_summary(self, project: CodeProject) -> dict:
        """
        Generate summary of the generated project.

        Args:
            project: Generated CodeProject

        Returns:
            Summary dictionary
        """
        total_lines = sum(
            len(f.content.split("\n")) for f in project.files
        )

        return {
            "name": project.name,
            "description": project.description,
            "file_count": len(project.files),
            "files": [f.filename for f in project.files],
            "total_lines": total_lines,
            "requirements": project.requirements,
            "python_version": project.python_version,
            "usage": project.usage,
            "entrypoint": project.get_entrypoint().filename if project.get_entrypoint() else None,
        }

"""
Debugger Agent - Analyze errors and fix generated code

This agent analyzes execution errors and uses LLM to generate
fixes for the generated code.
"""

import json
from typing import Optional

from ..models.code_project import CodeProject, CodeFile, ExecutionResult, ExecutionStatus
from ..tools.llm_client import LLMClient


class DebuggerAgent:
    """
    Agent for debugging and fixing generated code.

    This agent analyzes execution errors, identifies root causes,
    and generates fixes using LLM.

    Attributes:
        llm_client: LLM client for debugging
        max_fix_attempts: Maximum fix attempts per error

    Example:
        >>> agent = DebuggerAgent()
        >>> fixed_project = agent.fix(project, execution_result)
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_fix_attempts: int = 2,
    ):
        """
        Initialize the Debugger Agent.

        Args:
            llm_client: Optional LLM client instance
            max_fix_attempts: Maximum attempts to fix a single error
        """
        self.llm_client = llm_client or LLMClient()
        self.max_fix_attempts = max_fix_attempts

    def fix(
        self,
        project: CodeProject,
        execution_result: ExecutionResult,
        context: str = "",
    ) -> CodeProject:
        """
        Attempt to fix code based on execution error.

        Args:
            project: CodeProject that failed execution
            execution_result: The execution result with error
            context: Additional context about the algorithm

        Returns:
            Fixed CodeProject

        Raises:
            ValueError: If fix cannot be generated
        """
        if execution_result.status == ExecutionStatus.SUCCESS:
            return project

        # Get error information
        error_info = self._extract_error_info(execution_result)

        # Get all code as string
        code_str = self._project_to_string(project)

        # Use LLM to debug
        fix_result = self.llm_client.debug_code(
            code=code_str,
            error=error_info,
            context=context,
        )

        if fix_result.get("parse_error"):
            raise ValueError(f"Failed to generate fix: {fix_result.get('raw_response', 'Unknown')}")

        # Apply fix to project
        fixed_project = self._apply_fix(project, fix_result)

        return fixed_project

    def analyze_error(self, execution_result: ExecutionResult) -> dict:
        """
        Analyze execution error without generating fix.

        Args:
            execution_result: Execution result with error

        Returns:
            Error analysis dictionary
        """
        return {
            "status": execution_result.status.value,
            "error_type": execution_result.error_type,
            "error_message": execution_result.error_message,
            "error_line": execution_result.error_line,
            "stderr": execution_result.stderr,
            "category": self._categorize_error(execution_result),
            "fixable": self._is_likely_fixable(execution_result),
        }

    def _extract_error_info(self, result: ExecutionResult) -> str:
        """Extract error information as string."""
        parts = []

        if result.error_type:
            parts.append(f"Error Type: {result.error_type}")

        if result.error_message:
            parts.append(f"Message: {result.error_message}")

        if result.error_line:
            parts.append(f"Line: {result.error_line}")

        if result.stderr:
            parts.append(f"\nFull Traceback:\n{result.stderr}")

        return "\n".join(parts) if parts else "Unknown error occurred"

    def _project_to_string(self, project: CodeProject) -> str:
        """Convert project files to string representation."""
        parts = []
        for file in project.files:
            parts.append(f"# === File: {file.filename} ===")
            # Add line numbers for easier debugging
            lines = file.content.split("\n")
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            parts.append("\n".join(numbered))
            parts.append("")

        return "\n".join(parts)

    def _apply_fix(self, project: CodeProject, fix_result: dict) -> CodeProject:
        """
        Apply fix result to project.

        Args:
            project: Original project
            fix_result: Fix result from LLM

        Returns:
            Fixed project
        """
        # Check if we have fixed_files
        if "fixed_files" in fix_result:
            new_files = []
            for fixed_file in fix_result["fixed_files"]:
                new_files.append(CodeFile(
                    filename=fixed_file.get("filename", "unknown.py"),
                    path=fixed_file.get("path", fixed_file.get("filename")),
                    content=fixed_file.get("content", ""),
                    description=fixed_file.get("description", ""),
                    is_entrypoint=fixed_file.get("is_entrypoint", False),
                ))

            # Preserve entrypoint if not specified
            if not any(f.is_entrypoint for f in new_files):
                for orig in project.files:
                    if orig.is_entrypoint:
                        for new in new_files:
                            if new.filename == orig.filename:
                                new.is_entrypoint = True
                                break

            project.files = new_files

        # Apply individual changes if specified
        elif "fix" in fix_result and "changes" in fix_result["fix"]:
            for change in fix_result["fix"]["changes"]:
                filename = change.get("file")
                original = change.get("original", "")
                fixed = change.get("fixed", "")

                for file in project.files:
                    if file.filename == filename:
                        file.content = file.content.replace(original, fixed)

        # Handle fixed_code for single file fixes
        elif "fixed_code" in fix_result:
            fixed_code = fix_result["fixed_code"]
            # Apply to main file
            entrypoint = project.get_entrypoint()
            if entrypoint:
                entrypoint.content = fixed_code
            elif project.files:
                project.files[0].content = fixed_code

        # Update requirements if needed
        if fix_result.get("additional_requirements"):
            existing = set(project.requirements)
            for req in fix_result["additional_requirements"]:
                existing.add(req)
            project.requirements = list(existing)

        return project

    def _categorize_error(self, result: ExecutionResult) -> str:
        """Categorize error for better handling."""
        error_type = result.error_type or ""
        error_msg = (result.error_message or "").lower()
        stderr = (result.stderr or "").lower()

        if result.status == ExecutionStatus.TIMEOUT:
            return "timeout"

        if "syntaxerror" in error_type.lower():
            return "syntax"

        if "importerror" in error_type.lower() or "modulenotfounderror" in error_type.lower():
            return "import"

        if "typeerror" in error_type.lower():
            return "type"

        if "valueerror" in error_type.lower():
            return "value"

        if "indexerror" in error_type.lower() or "keyerror" in error_type.lower():
            return "index"

        if "attributeerror" in error_type.lower():
            return "attribute"

        if "shape" in error_msg or "dimension" in error_msg:
            return "shape_mismatch"

        if "memory" in error_msg or "killed" in stderr:
            return "memory"

        return "runtime"

    def _is_likely_fixable(self, result: ExecutionResult) -> bool:
        """Determine if error is likely fixable by code changes."""
        category = self._categorize_error(result)

        # These are usually fixable
        fixable_categories = {
            "syntax",
            "import",
            "type",
            "value",
            "index",
            "attribute",
            "shape_mismatch",
        }

        # These are usually not fixable by code changes
        unfixable_categories = {
            "timeout",
            "memory",
        }

        if category in unfixable_categories:
            return False

        return category in fixable_categories

    def suggest_fix_strategy(self, result: ExecutionResult) -> dict:
        """
        Suggest fix strategy based on error analysis.

        Args:
            result: Execution result with error

        Returns:
            Dictionary with fix suggestions
        """
        category = self._categorize_error(result)

        strategies = {
            "syntax": {
                "approach": "Check for missing colons, parentheses, or indentation errors",
                "common_fixes": ["Fix indentation", "Add missing colon", "Balance parentheses"],
            },
            "import": {
                "approach": "Add missing package to requirements or fix import path",
                "common_fixes": ["Add package to requirements.txt", "Use alternative library", "Check import path"],
            },
            "type": {
                "approach": "Check data types and add type conversions if needed",
                "common_fixes": ["Add type conversion", "Check None values", "Verify array shapes"],
            },
            "value": {
                "approach": "Validate input values and add error handling",
                "common_fixes": ["Add input validation", "Handle edge cases", "Check array dimensions"],
            },
            "index": {
                "approach": "Check array bounds and dictionary keys",
                "common_fixes": ["Add bounds checking", "Use .get() for dictionaries", "Verify array shapes"],
            },
            "attribute": {
                "approach": "Check object initialization and method names",
                "common_fixes": ["Initialize missing attribute", "Check for typos", "Verify class definition"],
            },
            "shape_mismatch": {
                "approach": "Verify tensor/array shapes and add reshaping",
                "common_fixes": ["Transpose arrays", "Reshape tensors", "Check broadcasting rules"],
            },
            "timeout": {
                "approach": "Optimize algorithm or reduce input size",
                "common_fixes": ["Reduce iterations", "Use vectorization", "Add early stopping"],
                "note": "May require algorithm changes rather than bug fixes",
            },
            "memory": {
                "approach": "Reduce memory usage or process in batches",
                "common_fixes": ["Use generators", "Process in batches", "Clear unused variables"],
                "note": "May require Docker memory limit increase",
            },
        }

        return strategies.get(category, {
            "approach": "General debugging: review error message and traceback",
            "common_fixes": ["Check variable types", "Add error handling", "Review algorithm logic"],
        })

    def get_fix_summary(self, fix_result: dict) -> str:
        """
        Generate human-readable summary of fix.

        Args:
            fix_result: Fix result from fix()

        Returns:
            Summary string
        """
        lines = []

        if "error_analysis" in fix_result:
            analysis = fix_result["error_analysis"]
            lines.append(f"Error Type: {analysis.get('error_type', 'Unknown')}")
            lines.append(f"Root Cause: {analysis.get('root_cause', 'Unknown')}")

        if "fix" in fix_result:
            fix = fix_result["fix"]
            lines.append(f"\nFix Description: {fix.get('description', 'N/A')}")

            if "changes" in fix:
                lines.append(f"Changes Made: {len(fix['changes'])}")
                for i, change in enumerate(fix["changes"], 1):
                    lines.append(f"  {i}. {change.get('file', 'unknown')}: {change.get('explanation', 'N/A')}")

        if fix_result.get("confidence"):
            lines.append(f"\nConfidence: {fix_result['confidence']*100:.0f}%")

        if fix_result.get("notes"):
            lines.append(f"Notes: {fix_result['notes']}")

        return "\n".join(lines) if lines else "No fix summary available"

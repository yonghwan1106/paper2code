"""
Executor Agent - Execute generated code in sandbox environment

This agent executes generated Python code in a safe environment
(Docker or subprocess) and captures execution results.
"""

import tempfile
from pathlib import Path
from typing import Optional

from ..models.code_project import CodeProject, ExecutionResult, ExecutionStatus
from ..tools.code_runner import CodeRunner


class ExecutorAgent:
    """
    Agent for executing generated code projects.

    This agent handles safe execution of generated code in Docker
    containers or subprocess fallback, capturing output and errors.

    Attributes:
        code_runner: Code execution tool
        use_docker: Whether to use Docker for execution
        timeout: Default execution timeout in seconds

    Example:
        >>> agent = ExecutorAgent()
        >>> result = agent.execute(project)
        >>> if result.status == ExecutionStatus.SUCCESS:
        ...     print(result.stdout)
    """

    def __init__(
        self,
        use_docker: bool = True,
        timeout: int = 120,
    ):
        """
        Initialize the Executor Agent.

        Args:
            use_docker: Whether to use Docker for sandboxed execution
            timeout: Default timeout in seconds
        """
        self.code_runner = CodeRunner(use_docker=use_docker)
        self.use_docker = self.code_runner.use_docker
        self.timeout = timeout

    def execute(
        self,
        project: CodeProject,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute a code project.

        Args:
            project: CodeProject to execute
            timeout: Execution timeout in seconds

        Returns:
            ExecutionResult with status, output, and any errors

        Example:
            >>> result = agent.execute(project)
            >>> print(result.stdout)
        """
        timeout = timeout or self.timeout

        # Validate project before execution
        validation = self.validate_project(project)
        if not validation["valid"]:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Project validation failed: {validation['errors']}",
            )

        # Execute using code runner
        result = self.code_runner.run_project(project, timeout=timeout)

        return result

    def execute_code(
        self,
        code: str,
        requirements: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute a single code string.

        Args:
            code: Python code to execute
            requirements: Required packages
            timeout: Execution timeout

        Returns:
            ExecutionResult

        Example:
            >>> result = agent.execute_code("print('Hello')")
            >>> print(result.stdout)  # "Hello\\n"
        """
        timeout = timeout or self.timeout

        # Validate syntax first
        is_valid, error = self.code_runner.validate_syntax(code)
        if not is_valid:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=error,
                error_type="SyntaxError",
            )

        return self.code_runner.run_code(code, requirements, timeout)

    def validate_project(self, project: CodeProject) -> dict:
        """
        Validate project before execution.

        Args:
            project: CodeProject to validate

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Check for files
        if not project.files:
            errors.append("Project has no files")

        # Check for entrypoint
        entrypoint = project.get_entrypoint()
        if not entrypoint:
            errors.append("No entry point file found")

        # Validate syntax of all Python files
        for file in project.files:
            if file.filename.endswith(".py"):
                is_valid, error = self.code_runner.validate_syntax(file.content)
                if not is_valid:
                    errors.append(f"Syntax error in {file.filename}: {error}")

        # Check for potentially dangerous patterns
        dangerous_patterns = self._check_dangerous_patterns(project)
        if dangerous_patterns:
            warnings.extend(dangerous_patterns)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_dangerous_patterns(self, project: CodeProject) -> list[str]:
        """
        Check for potentially dangerous code patterns.

        Args:
            project: CodeProject to check

        Returns:
            List of warning messages
        """
        warnings = []
        dangerous_imports = [
            "subprocess",
            "os.system",
            "eval(",
            "exec(",
            "__import__",
            "open(",  # File I/O can be dangerous
        ]

        for file in project.files:
            for pattern in dangerous_imports:
                if pattern in file.content:
                    warnings.append(
                        f"Potentially dangerous pattern '{pattern}' found in {file.filename}"
                    )

        return warnings

    def save_and_execute(
        self,
        project: CodeProject,
        output_dir: str | Path,
        timeout: Optional[int] = None,
    ) -> tuple[Path, ExecutionResult]:
        """
        Save project to directory and execute.

        Args:
            project: CodeProject to save and execute
            output_dir: Directory to save files
            timeout: Execution timeout

        Returns:
            Tuple of (project_path, ExecutionResult)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save project files
        project_path = output_dir / project.name
        project.save_to_directory(project_path)

        # Execute
        result = self.execute(project, timeout)

        return project_path, result

    def test_environment(self) -> dict:
        """
        Test the execution environment.

        Returns:
            Dictionary with environment status
        """
        result = {
            "docker_available": self.use_docker,
            "python_available": True,
            "test_execution": None,
        }

        # Test basic Python execution
        test_code = """
import sys
print(f"Python {sys.version}")
print("Test successful!")
"""

        test_result = self.execute_code(test_code, timeout=30)

        result["test_execution"] = {
            "status": test_result.status.value,
            "stdout": test_result.stdout,
            "stderr": test_result.stderr,
            "execution_time": test_result.execution_time,
        }

        return result

    def get_execution_summary(self, result: ExecutionResult) -> str:
        """
        Generate human-readable summary of execution result.

        Args:
            result: ExecutionResult to summarize

        Returns:
            Summary string
        """
        lines = [
            f"Status: {result.status.value}",
        ]

        if result.execution_time:
            lines.append(f"Execution Time: {result.execution_time:.2f}s")

        if result.status == ExecutionStatus.SUCCESS:
            if result.stdout:
                lines.append(f"\nOutput:\n{result.stdout[:1000]}")
                if len(result.stdout) > 1000:
                    lines.append("... (truncated)")
        else:
            if result.error_message:
                lines.append(f"\nError: {result.error_message}")
            if result.error_type:
                lines.append(f"Error Type: {result.error_type}")
            if result.error_line:
                lines.append(f"Error Line: {result.error_line}")
            if result.stderr:
                lines.append(f"\nStderr:\n{result.stderr[:500]}")

        return "\n".join(lines)

    def execute_with_retry(
        self,
        project: CodeProject,
        max_retries: int = 2,
        fix_callback: Optional[callable] = None,
    ) -> tuple[ExecutionResult, int]:
        """
        Execute with automatic retry on failure.

        Args:
            project: CodeProject to execute
            max_retries: Maximum retry attempts
            fix_callback: Optional callback to fix code on failure
                          Should accept (project, error) and return fixed project

        Returns:
            Tuple of (final ExecutionResult, number of attempts)

        Example:
            >>> result, attempts = agent.execute_with_retry(project, max_retries=2)
            >>> print(f"Succeeded after {attempts} attempts")
        """
        attempts = 0
        current_project = project

        while attempts <= max_retries:
            attempts += 1
            result = self.execute(current_project)

            if result.status == ExecutionStatus.SUCCESS:
                return result, attempts

            if result.status == ExecutionStatus.TIMEOUT:
                # Timeout is likely not fixable by code changes
                return result, attempts

            # Try to fix if callback provided and not last attempt
            if fix_callback and attempts <= max_retries:
                try:
                    current_project = fix_callback(
                        current_project,
                        result.stderr or result.error_message,
                    )
                except Exception:
                    # If fix fails, return current result
                    return result, attempts

        return result, attempts

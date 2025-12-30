"""
Code Runner Tool - Execute Python code in Docker sandbox
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from ..config import get_config
from ..models.code_project import CodeProject, ExecutionResult, ExecutionStatus


class CodeRunner:
    """Execute Python code safely in Docker container or subprocess"""

    def __init__(self, use_docker: bool = True):
        """
        Initialize code runner

        Args:
            use_docker: Whether to use Docker for sandboxed execution
        """
        self.config = get_config()
        self.use_docker = use_docker and self._check_docker_available()

    def _check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def run_project(self, project: CodeProject, timeout: Optional[int] = None) -> ExecutionResult:
        """
        Execute a code project

        Args:
            project: CodeProject to execute
            timeout: Execution timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
        timeout = timeout or self.config.docker.timeout

        # Create temporary directory for project
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write project files
            for file in project.files:
                file_path = tmpdir_path / file.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file.content, encoding="utf-8")

            # Write requirements.txt
            if project.requirements:
                req_path = tmpdir_path / "requirements.txt"
                req_path.write_text("\n".join(project.requirements), encoding="utf-8")

            # Get entry point
            entrypoint = project.get_entrypoint()
            if not entrypoint:
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error_message="No entry point found in project",
                )

            # Execute
            if self.use_docker:
                return self._run_in_docker(tmpdir_path, entrypoint.path, timeout)
            else:
                return self._run_subprocess(tmpdir_path, entrypoint.path, timeout)

    def run_code(
        self,
        code: str,
        requirements: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """
        Execute a single code string

        Args:
            code: Python code to execute
            requirements: Required packages
            timeout: Execution timeout

        Returns:
            ExecutionResult
        """
        timeout = timeout or self.config.docker.timeout

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write code file
            code_path = tmpdir_path / "main.py"
            code_path.write_text(code, encoding="utf-8")

            # Write requirements if any
            if requirements:
                req_path = tmpdir_path / "requirements.txt"
                req_path.write_text("\n".join(requirements), encoding="utf-8")

            # Execute
            if self.use_docker:
                return self._run_in_docker(tmpdir_path, "main.py", timeout)
            else:
                return self._run_subprocess(tmpdir_path, "main.py", timeout)

    def _run_in_docker(
        self,
        workdir: Path,
        entrypoint: str,
        timeout: int,
    ) -> ExecutionResult:
        """Run code in Docker container"""
        start_time = time.time()

        # Build Docker command
        docker_image = self.config.docker.image

        # Create a simple run script
        run_script = f"""#!/bin/bash
set -e
cd /app
if [ -f requirements.txt ]; then
    pip install -q -r requirements.txt 2>/dev/null || true
fi
python {entrypoint}
"""
        run_script_path = workdir / "run.sh"
        run_script_path.write_text(run_script)

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--network=none",  # No network access for security
            f"--memory={self.config.docker.memory_limit}",
            f"--cpus={self.config.docker.cpu_limit}",
            "-v", f"{workdir}:/app:ro",
            "-w", "/app",
            docker_image,
            "bash", "/app/run.sh",
        ]

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=0,
                    execution_time=execution_time,
                )
            else:
                error_info = self._parse_error(result.stderr)
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                    execution_time=execution_time,
                    error_message=error_info.get("message"),
                    error_type=error_info.get("type"),
                    error_line=error_info.get("line"),
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Execution timed out after {timeout} seconds",
                execution_time=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Docker execution failed: {str(e)}",
            )

    def _run_subprocess(
        self,
        workdir: Path,
        entrypoint: str,
        timeout: int,
    ) -> ExecutionResult:
        """Run code in subprocess (fallback when Docker unavailable)"""
        start_time = time.time()

        # Install requirements if present
        req_path = workdir / "requirements.txt"
        if req_path.exists():
            try:
                subprocess.run(
                    ["pip", "install", "-q", "-r", str(req_path)],
                    capture_output=True,
                    timeout=120,
                )
            except Exception:
                pass  # Continue even if install fails

        try:
            result = subprocess.run(
                ["python", str(workdir / entrypoint)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(workdir),
                env={**os.environ, "PYTHONPATH": str(workdir)},
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=0,
                    execution_time=execution_time,
                )
            else:
                error_info = self._parse_error(result.stderr)
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                    execution_time=execution_time,
                    error_message=error_info.get("message"),
                    error_type=error_info.get("type"),
                    error_line=error_info.get("line"),
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Execution timed out after {timeout} seconds",
                execution_time=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                error_message=f"Subprocess execution failed: {str(e)}",
            )

    def _parse_error(self, stderr: str) -> dict:
        """Parse error information from stderr"""
        result = {
            "message": stderr,
            "type": None,
            "line": None,
        }

        # Common Python error patterns
        import re

        # Match error type
        error_type_match = re.search(r"(\w+Error|\w+Exception):", stderr)
        if error_type_match:
            result["type"] = error_type_match.group(1)

        # Match line number
        line_match = re.search(r'line (\d+)', stderr)
        if line_match:
            result["line"] = int(line_match.group(1))

        # Get last line as error message
        lines = stderr.strip().split("\n")
        if lines:
            result["message"] = lines[-1]

        return result

    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate Python syntax without executing

        Args:
            code: Python code string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            compile(code, "<string>", "exec")
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

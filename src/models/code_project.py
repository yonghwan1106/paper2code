"""
Code Project Data Models - Represents generated code structure
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Code execution status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class CodeFile(BaseModel):
    """Represents a single code file"""

    filename: str = Field(description="File name (e.g., 'main.py')")
    path: str = Field(description="Relative path within project")
    content: str = Field(description="File content")
    language: str = Field(default="python", description="Programming language")
    description: Optional[str] = Field(default=None, description="File description")
    is_entrypoint: bool = Field(default=False, description="Is this the main entry point")


class ExecutionResult(BaseModel):
    """Represents code execution result"""

    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    return_code: int = Field(default=-1, description="Process return code")
    execution_time: float = Field(default=0.0, description="Execution time in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_type: Optional[str] = Field(default=None, description="Type of error (SyntaxError, etc.)")
    error_line: Optional[int] = Field(default=None, description="Line number of error")

    @property
    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.SUCCESS and self.return_code == 0

    @property
    def has_error(self) -> bool:
        """Check if there was an error"""
        return self.status == ExecutionStatus.ERROR or self.return_code != 0

    def get_error_context(self) -> str:
        """Get error context for debugging"""
        if not self.has_error:
            return ""

        parts = []
        if self.error_type:
            parts.append(f"Error Type: {self.error_type}")
        if self.error_line:
            parts.append(f"Line: {self.error_line}")
        if self.error_message:
            parts.append(f"Message: {self.error_message}")
        if self.stderr:
            parts.append(f"Stderr:\n{self.stderr}")

        return "\n".join(parts)


class CodeDesign(BaseModel):
    """Represents the code architecture design"""

    classes: list[dict] = Field(
        default_factory=list,
        description="List of classes with name, methods, attributes",
    )
    functions: list[dict] = Field(
        default_factory=list,
        description="List of standalone functions",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Required imports",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="External package dependencies",
    )
    file_structure: list[str] = Field(
        default_factory=list,
        description="Planned file structure",
    )
    entrypoint: str = Field(
        default="main.py",
        description="Main entry point file",
    )


class CodeProject(BaseModel):
    """Represents a complete generated code project"""

    # Project info
    name: str = Field(description="Project name")
    description: str = Field(default="", description="Project description")
    source_paper: Optional[str] = Field(default=None, description="Source paper title")

    # Code structure
    files: list[CodeFile] = Field(default_factory=list, description="Project files")
    design: Optional[CodeDesign] = Field(default=None, description="Code design")

    # Dependencies
    requirements: list[str] = Field(
        default_factory=list,
        description="Python package requirements",
    )
    python_version: str = Field(default="3.11", description="Required Python version")

    # Usage info
    usage: str = Field(default="python main.py", description="How to run the code")
    notes: str = Field(default="", description="Implementation notes")
    domain: str = Field(default="unknown", description="Paper domain")

    # Execution
    execution_results: list[ExecutionResult] = Field(
        default_factory=list,
        description="History of execution attempts",
    )
    debug_history: list[dict] = Field(
        default_factory=list,
        description="History of debug attempts",
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    generation_model: str = Field(default="claude-opus-4-20250514")
    total_tokens_used: int = Field(default=0)

    def get_entrypoint(self) -> Optional[CodeFile]:
        """Get the main entry point file"""
        for f in self.files:
            if f.is_entrypoint:
                return f
        # Fallback to main.py
        for f in self.files:
            if f.filename == "main.py":
                return f
        return self.files[0] if self.files else None

    def get_file(self, filename: str) -> Optional[CodeFile]:
        """Get a specific file by name"""
        for f in self.files:
            if f.filename == filename or f.path == filename:
                return f
        return None

    def get_requirements_txt(self) -> str:
        """Generate requirements.txt content"""
        return "\n".join(sorted(set(self.requirements)))

    def get_latest_result(self) -> Optional[ExecutionResult]:
        """Get the most recent execution result"""
        return self.execution_results[-1] if self.execution_results else None

    def is_working(self) -> bool:
        """Check if the code is currently working"""
        result = self.get_latest_result()
        return result is not None and result.is_success

    def add_execution_result(self, result: ExecutionResult) -> None:
        """Add an execution result to history"""
        self.execution_results.append(result)

    def add_debug_attempt(self, error: str, fix: str, result: ExecutionResult) -> None:
        """Record a debug attempt"""
        self.debug_history.append(
            {
                "error": error,
                "fix": fix,
                "result": result.model_dump(),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_directory_structure(self) -> str:
        """Generate directory structure representation"""
        lines = [f"{self.name}/"]
        for f in self.files:
            lines.append(f"├── {f.path}")
        lines.append("├── requirements.txt")
        lines.append("└── README.md")
        return "\n".join(lines)

    def save_to_directory(self, output_dir) -> None:
        """Save project files to a directory"""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save code files
        for file in self.files:
            file_path = output_path / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding="utf-8")

        # Save requirements.txt
        if self.requirements:
            req_path = output_path / "requirements.txt"
            req_path.write_text(self.get_requirements_txt(), encoding="utf-8")

        # Save README.md
        readme_content = f"""# {self.name}

{self.description}

## Usage

```bash
{self.usage}
```

## Requirements

- Python {self.python_version}
- Dependencies: see requirements.txt

## Notes

{self.notes}
"""
        readme_path = output_path / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")

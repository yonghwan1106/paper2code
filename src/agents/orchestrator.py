"""
Paper2Code Orchestrator - LangGraph-based workflow coordination

This module implements the main orchestrator that coordinates all agents
using LangGraph for state management and workflow control.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END

from ..models.paper import Paper
from ..models.code_project import CodeProject, ExecutionResult, ExecutionStatus
from ..tools.llm_client import LLMClient
from .parser import ParserAgent
from .analyzer import AnalyzerAgent
from .generator import GeneratorAgent
from .executor import ExecutorAgent
from .debugger import DebuggerAgent


class WorkflowStatus(str, Enum):
    """Status of the Paper2Code workflow."""
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    EXECUTING = "executing"
    DEBUGGING = "debugging"
    SUCCESS = "success"
    FAILED = "failed"


class Paper2CodeState(TypedDict):
    """
    State for the Paper2Code workflow.

    This TypedDict defines all state that flows through the LangGraph workflow.
    """
    # Input
    paper_path: str
    output_dir: str

    # Processing state
    status: str
    current_step: str
    error_message: Optional[str]

    # Parsed data
    parsed_paper: Optional[dict]
    paper_summary: Optional[dict]

    # Analysis results
    algorithm_spec: Optional[dict]
    main_algorithm: Optional[dict]

    # Generated code
    code_project: Optional[dict]  # Serialized CodeProject

    # Execution results
    execution_result: Optional[dict]  # Serialized ExecutionResult
    execution_success: bool

    # Debug state
    debug_attempts: int
    max_debug_attempts: int
    debug_history: list[dict]

    # Final output
    final_output: Optional[dict]

    # Metadata
    start_time: str
    end_time: Optional[str]
    total_tokens: int


def create_initial_state(
    paper_path: str,
    output_dir: str = "./output",
    max_debug_attempts: int = 2,
) -> Paper2CodeState:
    """Create initial state for workflow."""
    return Paper2CodeState(
        paper_path=paper_path,
        output_dir=output_dir,
        status=WorkflowStatus.PENDING.value,
        current_step="init",
        error_message=None,
        parsed_paper=None,
        paper_summary=None,
        algorithm_spec=None,
        main_algorithm=None,
        code_project=None,
        execution_result=None,
        execution_success=False,
        debug_attempts=0,
        max_debug_attempts=max_debug_attempts,
        debug_history=[],
        final_output=None,
        start_time=datetime.now().isoformat(),
        end_time=None,
        total_tokens=0,
    )


class Paper2CodeOrchestrator:
    """
    Main orchestrator for the Paper2Code pipeline.

    Uses LangGraph to coordinate agents through the workflow:
    Parse -> Analyze -> Generate -> Execute -> (Debug) -> Done

    Attributes:
        parser: Parser agent
        analyzer: Analyzer agent
        generator: Generator agent
        executor: Executor agent
        debugger: Debugger agent
        llm_client: Shared LLM client
        graph: LangGraph workflow

    Example:
        >>> orchestrator = Paper2CodeOrchestrator()
        >>> result = orchestrator.run("paper.pdf", "./output")
        >>> print(result["status"])
    """

    def __init__(
        self,
        use_docker: bool = True,
        max_debug_attempts: int = 2,
    ):
        """
        Initialize the orchestrator with all agents.

        Args:
            use_docker: Whether to use Docker for execution
            max_debug_attempts: Maximum debug retry attempts
        """
        # Initialize shared LLM client
        self.llm_client = LLMClient()

        # Initialize agents
        self.parser = ParserAgent()
        self.analyzer = AnalyzerAgent(llm_client=self.llm_client)
        self.generator = GeneratorAgent(llm_client=self.llm_client)
        self.executor = ExecutorAgent(use_docker=use_docker)
        self.debugger = DebuggerAgent(llm_client=self.llm_client)

        self.max_debug_attempts = max_debug_attempts

        # Build workflow graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create graph with state type
        graph = StateGraph(Paper2CodeState)

        # Add nodes for each step
        graph.add_node("parse", self._parse_node)
        graph.add_node("analyze", self._analyze_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("execute", self._execute_node)
        graph.add_node("debug", self._debug_node)
        graph.add_node("finalize", self._finalize_node)

        # Set entry point
        graph.set_entry_point("parse")

        # Add edges
        graph.add_edge("parse", "analyze")
        graph.add_edge("analyze", "generate")
        graph.add_edge("generate", "execute")

        # Conditional edge after execution
        graph.add_conditional_edges(
            "execute",
            self._should_debug,
            {
                "debug": "debug",
                "finalize": "finalize",
            }
        )

        # After debug, execute again or finalize
        graph.add_conditional_edges(
            "debug",
            self._should_retry,
            {
                "execute": "execute",
                "finalize": "finalize",
            }
        )

        # Finalize ends the workflow
        graph.add_edge("finalize", END)

        return graph.compile()

    def _parse_node(self, state: Paper2CodeState) -> dict:
        """Parse PDF node."""
        try:
            state["status"] = WorkflowStatus.PARSING.value
            state["current_step"] = "Parsing PDF..."

            paper = self.parser.parse(state["paper_path"])
            parsed_dict = self.parser.parse_to_dict(state["paper_path"])
            summary = self.parser.get_summary(paper)

            return {
                "parsed_paper": parsed_dict,
                "paper_summary": summary,
                "current_step": "PDF parsed successfully",
            }

        except Exception as e:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_message": f"Parse failed: {str(e)}",
                "current_step": "Parse failed",
            }

    def _analyze_node(self, state: Paper2CodeState) -> dict:
        """Analyze algorithms node."""
        if state.get("status") == WorkflowStatus.FAILED.value:
            return {}

        try:
            state["status"] = WorkflowStatus.ANALYZING.value
            state["current_step"] = "Analyzing algorithms..."

            analysis = self.analyzer.analyze_from_dict(state["parsed_paper"])
            main_algo = self.analyzer.get_main_algorithm(analysis)

            return {
                "algorithm_spec": analysis,
                "main_algorithm": main_algo,
                "current_step": "Algorithm analysis complete",
                "total_tokens": state.get("total_tokens", 0) + self.llm_client.get_token_usage(),
            }

        except Exception as e:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_message": f"Analysis failed: {str(e)}",
                "current_step": "Analysis failed",
            }

    def _generate_node(self, state: Paper2CodeState) -> dict:
        """Generate code node."""
        if state.get("status") == WorkflowStatus.FAILED.value:
            return {}

        try:
            state["status"] = WorkflowStatus.GENERATING.value
            state["current_step"] = "Generating code..."

            # Get paper content for context
            paper_content = ""
            if state.get("parsed_paper"):
                paper_content = state["parsed_paper"].get("abstract", "")
                sections = state["parsed_paper"].get("sections", [])
                for sec in sections:
                    paper_content += f"\n\n{sec.get('content', '')}"

            project = self.generator.generate(
                state["algorithm_spec"],
                paper_content[:5000],
            )

            # Serialize project
            project_dict = {
                "name": project.name,
                "description": project.description,
                "files": [
                    {
                        "filename": f.filename,
                        "path": f.path,
                        "content": f.content,
                        "description": f.description,
                        "is_entrypoint": f.is_entrypoint,
                    }
                    for f in project.files
                ],
                "requirements": project.requirements,
                "python_version": project.python_version,
                "usage": project.usage,
                "notes": project.notes,
            }

            return {
                "code_project": project_dict,
                "current_step": "Code generated successfully",
                "total_tokens": state.get("total_tokens", 0) + self.llm_client.get_token_usage(),
            }

        except Exception as e:
            return {
                "status": WorkflowStatus.FAILED.value,
                "error_message": f"Generation failed: {str(e)}",
                "current_step": "Generation failed",
            }

    def _execute_node(self, state: Paper2CodeState) -> dict:
        """Execute code node."""
        if state.get("status") == WorkflowStatus.FAILED.value:
            return {}

        try:
            state["status"] = WorkflowStatus.EXECUTING.value
            state["current_step"] = "Executing code..."

            # Reconstruct project from dict
            project = self._dict_to_project(state["code_project"])

            # Execute
            result = self.executor.execute(project)

            # Serialize result
            result_dict = {
                "status": result.status.value,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.return_code,
                "execution_time": result.execution_time,
                "error_message": result.error_message,
                "error_type": result.error_type,
                "error_line": result.error_line,
            }

            success = result.status == ExecutionStatus.SUCCESS

            return {
                "execution_result": result_dict,
                "execution_success": success,
                "current_step": "Execution complete" if success else "Execution failed",
            }

        except Exception as e:
            return {
                "execution_result": {
                    "status": "error",
                    "error_message": str(e),
                },
                "execution_success": False,
                "current_step": "Execution error",
            }

    def _debug_node(self, state: Paper2CodeState) -> dict:
        """Debug and fix code node."""
        try:
            state["status"] = WorkflowStatus.DEBUGGING.value
            attempt = state.get("debug_attempts", 0) + 1
            state["current_step"] = f"Debugging (attempt {attempt})..."

            # Reconstruct project
            project = self._dict_to_project(state["code_project"])

            # Reconstruct execution result
            exec_dict = state["execution_result"]
            execution_result = ExecutionResult(
                status=ExecutionStatus(exec_dict["status"]),
                stdout=exec_dict.get("stdout"),
                stderr=exec_dict.get("stderr"),
                return_code=exec_dict.get("return_code"),
                execution_time=exec_dict.get("execution_time"),
                error_message=exec_dict.get("error_message"),
                error_type=exec_dict.get("error_type"),
                error_line=exec_dict.get("error_line"),
            )

            # Get context from algorithm spec
            context = ""
            if state.get("main_algorithm"):
                context = json.dumps(state["main_algorithm"], indent=2)

            # Attempt fix
            fixed_project = self.debugger.fix(project, execution_result, context)

            # Serialize fixed project
            fixed_dict = {
                "name": fixed_project.name,
                "description": fixed_project.description,
                "files": [
                    {
                        "filename": f.filename,
                        "path": f.path,
                        "content": f.content,
                        "description": f.description,
                        "is_entrypoint": f.is_entrypoint,
                    }
                    for f in fixed_project.files
                ],
                "requirements": fixed_project.requirements,
                "python_version": fixed_project.python_version,
                "usage": fixed_project.usage,
                "notes": fixed_project.notes,
            }

            # Record debug history
            debug_history = state.get("debug_history", [])
            debug_history.append({
                "attempt": attempt,
                "error": exec_dict.get("error_message"),
                "fix_applied": True,
            })

            return {
                "code_project": fixed_dict,
                "debug_attempts": attempt,
                "debug_history": debug_history,
                "current_step": f"Fix applied (attempt {attempt})",
                "total_tokens": state.get("total_tokens", 0) + self.llm_client.get_token_usage(),
            }

        except Exception as e:
            debug_history = state.get("debug_history", [])
            debug_history.append({
                "attempt": state.get("debug_attempts", 0) + 1,
                "error": str(e),
                "fix_applied": False,
            })

            return {
                "debug_attempts": state.get("debug_attempts", 0) + 1,
                "debug_history": debug_history,
                "current_step": f"Debug failed: {str(e)}",
            }

    def _finalize_node(self, state: Paper2CodeState) -> dict:
        """Finalize workflow node."""
        success = state.get("execution_success", False)
        status = WorkflowStatus.SUCCESS if success else WorkflowStatus.FAILED

        # Save project to output directory if successful
        output_path = None
        if success and state.get("code_project"):
            try:
                project = self._dict_to_project(state["code_project"])
                output_dir = Path(state["output_dir"])
                output_dir.mkdir(parents=True, exist_ok=True)
                project_path = output_dir / project.name
                project.save_to_directory(project_path)
                output_path = str(project_path)
            except Exception:
                pass

        # Safely extract nested values
        main_algo = state.get("main_algorithm") or {}
        code_proj = state.get("code_project") or {}
        exec_result = state.get("execution_result") or {}

        final_output = {
            "success": success,
            "paper_path": state["paper_path"],
            "output_path": output_path,
            "algorithm_name": main_algo.get("name", "Unknown"),
            "file_count": len(code_proj.get("files", [])),
            "execution_output": exec_result.get("stdout", ""),
            "debug_attempts": state.get("debug_attempts", 0),
            "total_tokens": state.get("total_tokens", 0),
        }

        return {
            "status": status.value,
            "final_output": final_output,
            "end_time": datetime.now().isoformat(),
            "current_step": "Complete" if success else "Failed",
        }

    def _should_debug(self, state: Paper2CodeState) -> str:
        """Determine if we should debug or finalize."""
        if state.get("status") == WorkflowStatus.FAILED.value:
            return "finalize"

        if state.get("execution_success", False):
            return "finalize"

        if state.get("debug_attempts", 0) >= state.get("max_debug_attempts", 2):
            return "finalize"

        return "debug"

    def _should_retry(self, state: Paper2CodeState) -> str:
        """Determine if we should retry execution or finalize."""
        if state.get("debug_attempts", 0) >= state.get("max_debug_attempts", 2):
            return "finalize"

        # Check if debug was successful (fix was applied)
        debug_history = state.get("debug_history", [])
        if debug_history and debug_history[-1].get("fix_applied"):
            return "execute"

        return "finalize"

    def _dict_to_project(self, project_dict: dict) -> CodeProject:
        """Convert dictionary back to CodeProject."""
        from ..models.code_project import CodeFile

        files = [
            CodeFile(
                filename=f["filename"],
                path=f.get("path", f["filename"]),
                content=f["content"],
                description=f.get("description", ""),
                is_entrypoint=f.get("is_entrypoint", False),
            )
            for f in project_dict.get("files", [])
        ]

        return CodeProject(
            name=project_dict.get("name", "project"),
            description=project_dict.get("description", ""),
            files=files,
            requirements=project_dict.get("requirements", []),
            python_version=project_dict.get("python_version", "3.11"),
            usage=project_dict.get("usage", ""),
            notes=project_dict.get("notes", ""),
        )

    def run(
        self,
        paper_path: str,
        output_dir: str = "./output",
        verbose: bool = False,
    ) -> dict:
        """
        Run the full Paper2Code pipeline.

        Args:
            paper_path: Path to input PDF
            output_dir: Directory for output files
            verbose: Whether to print progress

        Returns:
            Final state dictionary with results
        """
        # Create initial state
        initial_state = create_initial_state(
            paper_path=paper_path,
            output_dir=output_dir,
            max_debug_attempts=self.max_debug_attempts,
        )

        if verbose:
            print(f"Starting Paper2Code pipeline...")
            print(f"Input: {paper_path}")
            print(f"Output: {output_dir}")

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        if verbose:
            print(f"\nPipeline complete!")
            print(f"Status: {final_state.get('status')}")
            if final_state.get('final_output'):
                print(f"Output path: {final_state['final_output'].get('output_path')}")

        return final_state

    def run_step_by_step(
        self,
        paper_path: str,
        output_dir: str = "./output",
    ):
        """
        Generator that yields state after each step.

        Useful for streaming progress updates.

        Args:
            paper_path: Path to input PDF
            output_dir: Directory for output files

        Yields:
            State dictionary after each step
        """
        initial_state = create_initial_state(
            paper_path=paper_path,
            output_dir=output_dir,
            max_debug_attempts=self.max_debug_attempts,
        )

        for state in self.graph.stream(initial_state):
            yield state

    def get_workflow_summary(self, final_state: dict) -> str:
        """
        Generate human-readable summary of workflow execution.

        Args:
            final_state: Final state from run()

        Returns:
            Summary string
        """
        lines = [
            "=" * 50,
            "Paper2Code Execution Summary",
            "=" * 50,
            f"Status: {final_state.get('status', 'unknown')}",
            f"Paper: {final_state.get('paper_path', 'N/A')}",
            "",
        ]

        if final_state.get("paper_summary"):
            summary = final_state["paper_summary"]
            lines.extend([
                "Paper Summary:",
                f"  Title: {summary.get('title', 'N/A')}",
                f"  Sections: {summary.get('section_count', 0)}",
                f"  Equations: {summary.get('equation_count', 0)}",
                "",
            ])

        if final_state.get("main_algorithm"):
            algo = final_state["main_algorithm"]
            lines.extend([
                "Main Algorithm:",
                f"  Name: {algo.get('name', 'N/A')}",
                f"  Purpose: {algo.get('purpose', 'N/A')}",
                "",
            ])

        if final_state.get("final_output"):
            output = final_state["final_output"]
            lines.extend([
                "Results:",
                f"  Success: {output.get('success', False)}",
                f"  Files Generated: {output.get('file_count', 0)}",
                f"  Debug Attempts: {output.get('debug_attempts', 0)}",
                f"  Total Tokens: {output.get('total_tokens', 0)}",
                f"  Output Path: {output.get('output_path', 'N/A')}",
            ])

        if final_state.get("execution_result"):
            result = final_state["execution_result"]
            if result.get("stdout"):
                lines.extend([
                    "",
                    "Execution Output:",
                    result["stdout"][:500],
                ])

        lines.append("=" * 50)
        return "\n".join(lines)

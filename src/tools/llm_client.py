"""
LLM Client - Wrapper for Anthropic Claude API
"""

import json
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from ..config import get_config, get_prompt_path


class LLMClient:
    """Client for interacting with Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM client

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model name (defaults to config)
        """
        config = get_config()

        self.api_key = api_key or config.llm.api_key
        self.model = model or config.llm.model
        self.max_tokens = config.llm.max_tokens
        self.temperature = config.llm.temperature

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env file or pass directly."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.total_tokens_used = 0

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Get completion from Claude

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        messages = [{"role": "user", "content": prompt}]

        # Use streaming for long requests to avoid timeout
        collected_text = []
        input_tokens = 0
        output_tokens = 0

        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            system=system or "You are a helpful AI assistant specialized in scientific research and code generation.",
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                collected_text.append(text)

            # Get final message for token usage
            final_message = stream.get_final_message()
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens

        # Track token usage
        self.total_tokens_used += input_tokens + output_tokens

        return "".join(collected_text)

    def complete_with_template(
        self,
        template_name: str,
        variables: dict,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Get completion using a prompt template

        Args:
            template_name: Name of template file (without .md extension)
            variables: Variables to substitute in template
            system: System prompt override
            **kwargs: Additional arguments for complete()

        Returns:
            Generated text
        """
        template_path = get_prompt_path(template_name)

        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")

        template = template_path.read_text(encoding="utf-8")

        # Substitute variables
        prompt = template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        return self.complete(prompt, system=system, **kwargs)

    def analyze_algorithm(self, paper_content: str) -> dict:
        """
        Analyze paper content and extract algorithm specification

        Args:
            paper_content: Parsed paper content

        Returns:
            Algorithm specification as dict
        """
        system = """You are an expert at understanding scientific papers and extracting algorithms.
Your task is to analyze the given paper and extract detailed algorithm specifications.
Always respond with valid JSON."""

        prompt = f"""Analyze the following scientific paper and extract the main algorithm(s).

Paper Content:
{paper_content}

Extract and return a JSON object with:
{{
    "algorithms": [
        {{
            "name": "Algorithm name",
            "description": "What the algorithm does",
            "purpose": "Problem it solves",
            "inputs": [
                {{"name": "input_name", "type": "data type", "description": "what it is"}}
            ],
            "outputs": [
                {{"name": "output_name", "type": "data type", "description": "what it is"}}
            ],
            "steps": ["Step 1", "Step 2", ...],
            "dependencies": ["numpy", "torch", ...],
            "hyperparameters": [
                {{"name": "param_name", "default": "value", "description": "what it controls"}}
            ],
            "pseudocode": "If available, the pseudocode"
        }}
    ],
    "main_algorithm_index": 0
}}

Return ONLY the JSON, no other text."""

        response = self.complete(prompt, system=system)

        # Parse JSON from response (handle various formats)
        result = self._parse_json_response(response)

        # Ensure algorithms key exists
        if "algorithms" not in result and not result.get("parse_error"):
            result["algorithms"] = []

        return result

    def generate_code(self, algorithm_spec: dict, paper_context: str = "") -> dict:
        """
        Generate Python code from algorithm specification

        Args:
            algorithm_spec: Algorithm specification dict
            paper_context: Additional context from paper

        Returns:
            Generated code structure
        """
        system = """You are an expert Python programmer specializing in implementing scientific algorithms.
Generate clean, well-documented, production-quality Python code.
Always respond with valid JSON containing the code files."""

        prompt = f"""Generate Python code to implement the following algorithm.

Algorithm Specification:
{json.dumps(algorithm_spec, indent=2)}

Additional Context from Paper:
{paper_context[:2000] if paper_context else "None provided"}

Generate a complete, runnable Python project with:
1. Main implementation file
2. Requirements (pip packages needed)
3. A simple test/demo script

Return a JSON object:
{{
    "files": [
        {{
            "filename": "algorithm.py",
            "content": "# Python code here",
            "description": "Main implementation"
        }},
        {{
            "filename": "main.py",
            "content": "# Demo script",
            "description": "Entry point with example usage",
            "is_entrypoint": true
        }}
    ],
    "requirements": ["numpy", "torch", ...],
    "usage": "How to run the code"
}}

Return ONLY the JSON, no other text."""

        response = self.complete(prompt, system=system, max_tokens=16384)

        # Parse JSON from response (handle various formats)
        return self._parse_json_response(response)

    def debug_code(self, code: str, error: str, context: str = "") -> dict:
        """
        Analyze error and suggest fix

        Args:
            code: The code that failed
            error: Error message/traceback
            context: Additional context

        Returns:
            Fix suggestion
        """
        system = """You are an expert debugger. Analyze the error and provide a fix.
Return only the corrected code in JSON format."""

        prompt = f"""The following Python code has an error. Fix it.

Code:
```python
{code}
```

Error:
```
{error}
```

{f"Context: {context}" if context else ""}

Return a JSON object:
{{
    "fixed_code": "# The corrected Python code",
    "explanation": "What was wrong and how you fixed it",
    "changes": ["List of specific changes made"]
}}

Return ONLY the JSON, no other text."""

        response = self.complete(prompt, system=system)

        # Parse JSON from response (handle various formats)
        result = self._parse_json_response(response)

        # Ensure fixed_code key exists on parse error
        if result.get("parse_error") and "fixed_code" not in result:
            result["fixed_code"] = code
            result["explanation"] = "Failed to parse fix"

        return result

    def get_token_usage(self) -> int:
        """Get total tokens used"""
        return self.total_tokens_used

    def _parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response, handling various formats.

        Handles:
        - Raw JSON: {"files": [...]}
        - Markdown code blocks: ```json {...} ```
        - Word prefix: json {...}
        - Mixed formats with extra text

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict or error dict
        """
        import re

        # Try multiple parsing strategies
        strategies = [
            # Strategy 1: Direct JSON parse
            lambda r: json.loads(r.strip()),
            # Strategy 2: Extract from ```json ... ```
            lambda r: json.loads(r.split("```json")[1].split("```")[0].strip())
            if "```json" in r else None,
            # Strategy 3: Extract from ``` ... ```
            lambda r: json.loads(r.split("```")[1].split("```")[0].strip())
            if r.count("```") >= 2 else None,
            # Strategy 4: Handle "json {...}" format (word prefix without backticks)
            lambda r: json.loads(re.sub(r"^json\s*", "", r.strip(), flags=re.IGNORECASE))
            if r.strip().lower().startswith("json") else None,
            # Strategy 5: Find JSON object by braces
            lambda r: json.loads(r[r.find("{"):r.rfind("}") + 1])
            if "{" in r and "}" in r else None,
        ]

        for strategy in strategies:
            try:
                result = strategy(response)
                if result is not None and isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, IndexError, ValueError, TypeError):
                continue

        # All strategies failed
        return {
            "files": [],
            "requirements": [],
            "raw_response": response[:1000] + "..." if len(response) > 1000 else response,
            "parse_error": True,
        }

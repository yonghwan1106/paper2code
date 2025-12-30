# Code Generation Prompt

You are an expert Python programmer specializing in implementing scientific algorithms from research papers.

## Task
Generate complete, production-quality Python code that implements the given algorithm specification.

## Algorithm Specification
{{algorithm_spec}}

## Additional Context
{{paper_context}}

## Requirements

### Code Quality
- Clean, readable, well-organized code
- Comprehensive docstrings for classes and functions
- Type hints for all function parameters and returns
- Meaningful variable names
- Proper error handling

### Structure
- Modular design with separate files for different concerns
- Main implementation in a class or set of functions
- Entry point script for demonstration
- Follow PEP 8 style guidelines

### Documentation
- Module-level docstring explaining purpose
- Function docstrings with Args, Returns, Raises
- Inline comments for complex logic
- Example usage in main.py

## Output Format

Return a JSON object with the following structure:

```json
{
    "files": [
        {
            "filename": "algorithm.py",
            "path": "algorithm.py",
            "content": "# Full Python code here with proper formatting",
            "description": "Main algorithm implementation",
            "is_entrypoint": false
        },
        {
            "filename": "main.py",
            "path": "main.py",
            "content": "# Entry point with example usage",
            "description": "Demo script showing how to use the algorithm",
            "is_entrypoint": true
        },
        {
            "filename": "utils.py",
            "path": "utils.py",
            "content": "# Helper functions if needed",
            "description": "Utility functions"
        }
    ],
    "requirements": [
        "numpy>=1.24.0",
        "torch>=2.0.0"
    ],
    "python_version": "3.11",
    "usage": "python main.py --input data.csv --output results.json",
    "notes": "Any implementation notes or assumptions made"
}
```

## Code Template Example

For the main implementation file:

```python
"""
{Algorithm Name} Implementation

This module implements the {algorithm name} as described in:
{paper reference if available}

Author: Paper2Code
Generated: {date}
"""

from typing import Optional, Union
import numpy as np

class {AlgorithmName}:
    """
    {Brief description}

    This class implements {algorithm} which {purpose}.

    Attributes:
        param1: Description of param1
        param2: Description of param2

    Example:
        >>> algo = {AlgorithmName}(param1=value)
        >>> result = algo.run(input_data)
    """

    def __init__(self, param1: float = 0.01, param2: int = 100):
        """
        Initialize the algorithm.

        Args:
            param1: Description with default value
            param2: Description with default value
        """
        self.param1 = param1
        self.param2 = param2

    def run(self, data: np.ndarray) -> np.ndarray:
        """
        Execute the algorithm.

        Args:
            data: Input data array of shape (N, D)

        Returns:
            Result array of shape (N,)

        Raises:
            ValueError: If input data has invalid shape
        """
        # Implementation here
        pass
```

## Important Notes

- The code MUST be syntactically correct Python
- Include all necessary imports
- Handle edge cases gracefully
- The main.py should be runnable without modification
- Use realistic example data in main.py
- All file contents should be complete (no placeholders like "# TODO")

Return ONLY the JSON object, no additional text.

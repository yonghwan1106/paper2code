# Algorithm Analysis Prompt

You are an expert at understanding scientific papers and extracting algorithms for implementation.

## Task
Analyze the following scientific paper content and extract detailed algorithm specifications that can be used to generate executable code.

## Paper Content
{{paper_content}}

## Instructions

1. **Identify Algorithms**: Find all algorithms, methods, or procedures described in the paper
2. **Extract Details**: For each algorithm, extract:
   - Name and purpose
   - Input parameters with types and descriptions
   - Output format and types
   - Step-by-step procedure
   - Required dependencies (libraries like numpy, torch, etc.)
   - Hyperparameters with default values
   - Mathematical equations (if any)

3. **Prioritize**: Identify the main/core algorithm if multiple exist

## Output Format

Return a JSON object with the following structure:

```json
{
    "algorithms": [
        {
            "name": "Algorithm Name",
            "description": "Brief description of what it does",
            "purpose": "The problem it solves or task it performs",
            "inputs": [
                {
                    "name": "parameter_name",
                    "type": "numpy.ndarray | torch.Tensor | int | float | str | list",
                    "shape": "Optional shape description like (N, D) or (batch_size, seq_len)",
                    "description": "What this input represents"
                }
            ],
            "outputs": [
                {
                    "name": "output_name",
                    "type": "data type",
                    "shape": "Optional shape",
                    "description": "What this output represents"
                }
            ],
            "steps": [
                "1. Initialize parameters...",
                "2. For each iteration...",
                "3. Compute the loss...",
                "4. Update weights...",
                "5. Return results..."
            ],
            "dependencies": ["numpy", "torch", "scipy"],
            "hyperparameters": [
                {
                    "name": "learning_rate",
                    "type": "float",
                    "default": 0.001,
                    "description": "Step size for gradient updates"
                }
            ],
            "equations": [
                "\\mathbf{h}_t = \\sigma(\\mathbf{W}_h \\mathbf{x}_t + \\mathbf{b}_h)"
            ],
            "pseudocode": "Optional pseudocode from paper",
            "complexity": {
                "time": "O(n^2) or O(n log n)",
                "space": "O(n)"
            }
        }
    ],
    "main_algorithm_index": 0,
    "paper_domain": "machine_learning | optimization | signal_processing | etc",
    "implementation_notes": "Any additional notes for implementation"
}
```

## Important Notes

- Be precise about data types and shapes
- Include all necessary steps, don't skip "obvious" ones
- If equations are present, include them in LaTeX format
- Identify which libraries are needed (numpy, torch, tensorflow, etc.)
- If something is ambiguous in the paper, note it in implementation_notes

Return ONLY the JSON object, no additional text.

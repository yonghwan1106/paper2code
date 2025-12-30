# Paper2Code

**Scientific Paper → Executable Python Code**

AI Agent that automatically converts algorithms described in scientific papers into runnable Python implementations.

## Features

- **PDF Parsing**: Extract text, sections, equations, and pseudocode from scientific papers
- **Algorithm Analysis**: Use LLM to understand and extract algorithm specifications
- **Code Generation**: Generate production-quality Python code with proper documentation
- **Sandboxed Execution**: Run generated code safely in Docker containers
- **Auto-Debugging**: Automatically fix common errors with retry mechanism

## Architecture

```
Paper2Code Pipeline:
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
│ Parser  │ →  │ Analyzer │ →  │ Generator │ →  │ Executor │ →  │ Debugger │
│  Agent  │    │   Agent  │    │   Agent   │    │   Agent  │    │   Agent  │
└─────────┘    └──────────┘    └───────────┘    └──────────┘    └──────────┘
     ↓              ↓               ↓               ↓               ↓
   Paper         Algorithm        Python          Result          Fixed
   JSON           Spec            Code                             Code
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop (for sandboxed execution)
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/paper2code.git
cd paper2code

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

```bash
# Basic usage
python -m src.main --input paper.pdf --output ./output

# With verbose output
python -m src.main paper.pdf -o ./output -v

# Without Docker (use subprocess)
python -m src.main paper.pdf -o ./output --no-docker

# Specify max retry attempts
python -m src.main paper.pdf -o ./output --max-retries 3
```

### Docker Usage

```bash
# Build the image
docker-compose build

# Run interactively
docker-compose run paper2code

# Inside container
python -m src.main --input /app/papers/example.pdf --output /app/output
```

## Project Structure

```
paper2code/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration management
│   │
│   ├── agents/              # Multi-Agent system
│   │   ├── orchestrator.py  # LangGraph workflow
│   │   ├── parser.py        # PDF parsing agent
│   │   ├── analyzer.py      # Algorithm analysis agent
│   │   ├── generator.py     # Code generation agent
│   │   ├── executor.py      # Code execution agent
│   │   └── debugger.py      # Error fixing agent
│   │
│   ├── tools/               # Agent tools
│   │   ├── pdf_parser.py    # PyMuPDF wrapper
│   │   ├── llm_client.py    # Anthropic API client
│   │   └── code_runner.py   # Docker/subprocess runner
│   │
│   ├── prompts/             # LLM prompt templates
│   │   ├── analyzer.md
│   │   ├── generator.md
│   │   └── debugger.md
│   │
│   └── models/              # Data models
│       ├── paper.py         # Paper structure
│       └── code_project.py  # Generated code structure
│
├── tests/                   # Unit tests
├── examples/                # Example papers and outputs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Configuration

Environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `CLAUDE_MODEL` | Claude model name | claude-opus-4-20250514 |
| `MAX_TOKENS` | Max tokens per request | 8192 |
| `DOCKER_IMAGE` | Sandbox Docker image | paper2code-sandbox:latest |
| `DOCKER_TIMEOUT` | Execution timeout (seconds) | 120 |

## Example Output

Given a paper describing K-Means clustering, Paper2Code generates:

```python
# kmeans.py
"""
K-Means Clustering Implementation

Implements the K-Means clustering algorithm as described in the paper.
"""

import numpy as np
from typing import Optional

class KMeans:
    """K-Means clustering algorithm."""

    def __init__(self, n_clusters: int = 8, max_iter: int = 300):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.centroids = None

    def fit(self, X: np.ndarray) -> 'KMeans':
        """Fit K-Means to data."""
        # Implementation...
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict cluster labels."""
        # Implementation...
        pass
```

## Limitations (MVP)

- Only supports English papers
- PDF parsing may miss complex layouts
- Requires clear algorithm descriptions in the paper
- Limited to Python code generation
- Best with papers that include pseudocode

## Roadmap

- [ ] GROBID integration for better academic paper parsing
- [ ] RAG system with arXiv paper database
- [ ] Support for complex mathematical equations (SymPy)
- [ ] Figure and table verification
- [ ] Multi-language code generation
- [ ] Korean paper support

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## License

MIT License

## Acknowledgments

- Anthropic for Claude API
- LangChain/LangGraph for agent framework
- PyMuPDF for PDF parsing

"""
Paper2Code Configuration Management
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
PROMPTS_DIR = SRC_DIR / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"


class LLMConfig(BaseModel):
    """LLM Configuration"""

    api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = Field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "8192")))
    temperature: float = Field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.1")))


class DockerConfig(BaseModel):
    """Docker Execution Configuration"""

    image: str = Field(default_factory=lambda: os.getenv("DOCKER_IMAGE", "python:3.11-slim"))
    timeout: int = Field(default_factory=lambda: int(os.getenv("DOCKER_TIMEOUT", "300")))
    memory_limit: str = "2g"
    cpu_limit: float = 2.0


class AppConfig(BaseModel):
    """Application Configuration"""

    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_debug_attempts: int = 2  # Maximum auto-fix attempts


class Config(BaseModel):
    """Main Configuration Container"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    app: AppConfig = Field(default_factory=AppConfig)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment"""
        return cls()

    def validate_api_key(self) -> bool:
        """Check if API key is configured"""
        return bool(self.llm.api_key and self.llm.api_key != "your_anthropic_api_key_here")


# Global configuration instance
config = Config.load()


def get_config() -> Config:
    """Get the global configuration"""
    return config


def get_prompt_path(prompt_name: str) -> Path:
    """Get path to a prompt template file"""
    return PROMPTS_DIR / f"{prompt_name}.md"


def ensure_output_dir() -> Path:
    """Ensure output directory exists and return path"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR

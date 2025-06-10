"""Configuration settings and environment variables."""

import os
from pathlib import Path


class Settings:
    """Application settings and configuration."""
    
    # API Configuration
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    DEFAULT_MODEL = "gemini-2.5-flash-preview-05-20"
    
    # Cache Configuration
    CACHE_DIR = Path("cache")
    FILE_UPLOAD_TTL_HOURS = 48
    EXAMPLES_CACHE_TTL_MINUTES = 60
    
    # Default Directories
    DEFAULT_PAGES_DIR = Path("default_pages")
    EXAMPLES_DIR = Path("examples")
    PROMPTS_DIR = Path("prompts")
    LOGS_DIR = Path("logs")
    
    # Output Configuration
    DEFAULT_OUTPUT_DIR = Path("output")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Ensure directories exist
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
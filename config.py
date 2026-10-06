"""
Configuration management for PDF Text Extractor
Supports environment variable configuration and `.env` file loading
"""

import os
from pathlib import Path
from typing import Optional

# Load .env file if it exists
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)


class Config:
    """Base configuration"""
    
    # Backend
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").lower()
    
    # Application
    APP_NAME: str = "PDF Text Extractor"
    APP_VERSION: str = "1.0.0"
    
    # File Upload
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "160"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    TEMP_FILE_EXPIRY_HOURS: int = int(os.getenv("TEMP_FILE_EXPIRY_HOURS", "1"))
    
    # Security
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # LLM Settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    USE_GEMINI_FALLBACK: bool = True  # Always use Gemini
    
    # Derived values
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate configuration values"""
        errors = []
        
        if cls.MAX_PAGES < 1:
            errors.append("MAX_PAGES must be at least 1")
        
        if cls.MAX_FILE_SIZE_MB < 1:
            errors.append("MAX_FILE_SIZE_MB must be at least 1")
        
        if cls.PORT < 1 or cls.PORT > 65535:
            errors.append("PORT must be between 1 and 65535")
        
        valid_log_levels = {"debug", "info", "warning", "error", "critical"}
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}")
        
        return len(errors) == 0, errors


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = "debug"
    CORS_ORIGINS = ["*"]


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = "info"
    # Set specific domains in production
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://yourdomain.com").split(",")


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    LOG_LEVEL = "debug"
    MAX_FILE_SIZE_MB = 10
    MAX_PAGES = 5
    TEMP_FILE_EXPIRY_HOURS = 0.01
    UPLOAD_DIR = "test_uploads"


def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "production").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    
    config_class = config_map.get(env, ProductionConfig)
    
    # Validate configuration
    is_valid, errors = config_class.validate()
    if not is_valid:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))
    
    return config_class()


# Singleton instance
config = get_config()


def update_gemini_config(api_key: Optional[str] = None, model: Optional[str] = None):
    """Update Gemini configuration live and persist to .env file."""
    env_path = Path(__file__).parent / ".env"
    lines = []
    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            
    key_updated = False
    model_updated = False
    new_lines = []
    
    if api_key is not None:
        os.environ["GEMINI_API_KEY"] = api_key.strip()
        config.GEMINI_API_KEY = api_key.strip()
        
    if model is not None:
        os.environ["GEMINI_MODEL"] = model.strip()
        config.GEMINI_MODEL = model.strip()
        
    for line in lines:
        if line.startswith("GEMINI_API_KEY=") and api_key is not None:
            new_lines.append(f"GEMINI_API_KEY={api_key.strip()}\n")
            key_updated = True
        elif line.startswith("GEMINI_MODEL=") and model is not None:
            new_lines.append(f"GEMINI_MODEL={model.strip()}\n")
            model_updated = True
        else:
            new_lines.append(line)
            
    if not key_updated and api_key is not None:
        new_lines.append(f"GEMINI_API_KEY={api_key.strip()}\n")
    if not model_updated and model is not None:
        new_lines.append(f"GEMINI_MODEL={model.strip()}\n")
        
    with env_path.open("w", encoding="utf-8") as f:
        f.writelines(new_lines)

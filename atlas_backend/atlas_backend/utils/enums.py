from enum import Enum


class LLMModel(str, Enum):
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "md"
    HTML = "html"

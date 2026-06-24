"""Request models and input validation for the SecureGuard API.

The submitted code snippet is the primary untrusted input (see THREAT_MODEL),
so all constraints on it live here in one place.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

# A 10k-char cap keeps a single submission cheap and bounds Azure OpenAI token
# cost / latency (OWASP LLM10: Unbounded Consumption).
MAX_CODE_LENGTH = 10_000


class Language(str, Enum):
    """Languages the analyzer accepts. An enum (not a free str) means Pydantic
    rejects anything outside this set with a 422 automatically."""

    python = "python"
    javascript = "javascript"
    typescript = "typescript"
    java = "java"
    go = "go"
    ruby = "ruby"
    php = "php"
    csharp = "csharp"
    cpp = "cpp"
    c = "c"
    rust = "rust"
    kotlin = "kotlin"
    swift = "swift"
    sql = "sql"
    shell = "shell"
    other = "other"


class CodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_LENGTH)
    language: Language

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        # Reject null bytes outright (common in binary content / injection probes).
        if "\x00" in v:
            raise ValueError("Code must not contain null bytes")
        # Reject binary / non-text content: control characters other than the
        # common whitespace ones (tab, newline, carriage return).
        if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in v):
            raise ValueError("Code must be valid text, not binary content")
        return v

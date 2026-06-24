"""Preprocessing that runs BEFORE any LLM call.

Three jobs (Week 3, Tue):
1. Strip/flag comments — comments are a prime prompt-injection vector.
2. Normalize whitespace — remove zero-width / control chars used to smuggle
   instructions past filters; tidy line endings.
3. Extract imports — give the dependency analyzer a clean list to work with.

This is both preparation and a security control (OWASP LLM01 defense): removing
comment-borne payloads before the code reaches any model closes a whole class of
attacks at the door.
"""

import re

# Per-language comment syntax.
LINE_COMMENT = {
    "python": "#", "ruby": "#", "shell": "#",
    "javascript": "//", "typescript": "//", "java": "//", "go": "//",
    "c": "//", "cpp": "//", "rust": "//", "kotlin": "//", "swift": "//", "php": "//",
    "sql": "--",
}
BLOCK_COMMENT = {  # (open, close)
    lang: ("/*", "*/")
    for lang in ("javascript", "typescript", "java", "go", "c", "cpp", "rust", "kotlin", "swift", "php")
}

# Phrases that, if found inside a comment, suggest an injection attempt.
INJECTION_MARKERS = (
    "ignore previous", "ignore all", "disregard", "system:", "assistant:",
    "you are now", "new instructions", "instruction", "score 100", "prompt",
    "jailbreak", "override", "do not report", "respond with",
)

# Zero-width / direction-control characters used to smuggle hidden text.
INVISIBLE_CHARS = re.compile(r"[​‌‍⁠﻿\u202A-\u202E]")

# Import-extraction patterns by language family.
IMPORT_PATTERNS = {
    "python": [r"^\s*import\s+([\w.]+)", r"^\s*from\s+([\w.]+)\s+import"],
    "javascript": [r"""require\(['"]([^'"]+)['"]\)""", r"""import\s+.*\s+from\s+['"]([^'"]+)['"]"""],
    "typescript": [r"""require\(['"]([^'"]+)['"]\)""", r"""import\s+.*\s+from\s+['"]([^'"]+)['"]"""],
    "java": [r"^\s*import\s+([\w.]+);"],
    "go": [r"""^\s*import\s+"([^"]+)"""],
    "ruby": [r"""^\s*require\s+['"]([^'"]+)['"]"""],
    "php": [r"""^\s*use\s+([\w\\]+);"""],
}


def strip_comments(code: str, language: str) -> tuple[str, list[str]]:
    """Remove comments, returning (clean_code, flagged_comments).

    A comment is *flagged* if it contains an injection marker — so we can both
    report the attempt and ensure the payload never reaches the LLM.
    """
    flagged: list[str] = []

    def flag_if_suspicious(text: str) -> None:
        low = text.lower()
        if any(marker in low for marker in INJECTION_MARKERS):
            flagged.append(text.strip())

    # Block comments first (multi-line).
    block = BLOCK_COMMENT.get(language)
    if block:
        open_tok, close_tok = (re.escape(t) for t in block)
        for match in re.findall(f"{open_tok}.*?{close_tok}", code, flags=re.DOTALL):
            flag_if_suspicious(match)
        code = re.sub(f"{open_tok}.*?{close_tok}", "", code, flags=re.DOTALL)

    # Line comments.
    marker = LINE_COMMENT.get(language)
    if marker:
        cleaned_lines = []
        esc = re.escape(marker)
        for line in code.splitlines():
            m = re.search(esc, line)
            if m:
                flag_if_suspicious(line[m.start():])
                line = line[: m.start()].rstrip()
            cleaned_lines.append(line)
        code = "\n".join(cleaned_lines)

    return code, flagged


def normalize_whitespace(code: str) -> str:
    """Strip invisible/control chars, normalize line endings, collapse blank runs."""
    code = INVISIBLE_CHARS.sub("", code)
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    code = re.sub(r"\n{3,}", "\n\n", code)
    code = "\n".join(line.rstrip() for line in code.splitlines())
    return code.strip()


def extract_imports(code: str, language: str) -> list[str]:
    """Best-effort list of imported modules/packages for the dependency node."""
    found: list[str] = []
    for pattern in IMPORT_PATTERNS.get(language, []):
        for match in re.findall(pattern, code, flags=re.MULTILINE):
            if match not in found:
                found.append(match)
    return found


def preprocess(code: str, language: str) -> dict:
    """Run the full preprocessing pipeline; pure function, no LLM, no I/O."""
    clean, flagged = strip_comments(code, language)
    clean = normalize_whitespace(clean)
    imports = extract_imports(clean, language)
    return {
        "clean_code": clean,
        "comment_flags": flagged,
        "imports": imports,
    }

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    type: str
    count: int


@dataclass
class PIIScanResult:
    masked: str
    redactions: list[PIIMatch] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


# PII patterns for the Python fallback (ordered: most specific first)
_PII_PATTERNS: dict[str, re.Pattern] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "MRN": re.compile(r"\b(?:MRN|mrn)[:\s#]*\d{6,10}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "DOB": re.compile(
        r"\b(?:DOB|dob|Date of Birth|date of birth)[:\s]*"
        r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
    ),
    "PHONE": re.compile(
        r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
}

_MASK_CHAR = "[REDACTED]"


def _try_load_rust_scanner():
    """Attempt to import the Rust PyO3 scanner."""
    try:
        import sentinel_pii_scanner  # type: ignore[import-not-found]

        return sentinel_pii_scanner
    except ImportError:
        return None


class PIIScanner:
    def __init__(self, backend: str = "auto") -> None:
        self._rust_module = None
        self._backend = backend

        if backend in ("auto", "rust"):
            self._rust_module = _try_load_rust_scanner()
            if self._rust_module:
                self._backend = "rust"
                logger.info("PII scanner: using Rust backend")
            elif backend == "rust":
                raise ImportError(
                    "Rust PII scanner requested but sentinel_pii_scanner module not found"
                )

        if self._rust_module is None:
            self._backend = "python"
            logger.info("PII scanner: using Python fallback")

    @property
    def backend_name(self) -> str:
        return self._backend

    def scan(self, text: str) -> PIIScanResult:
        if self._rust_module:
            return self._scan_rust(text)
        return self._scan_python(text)

    def _scan_rust(self, text: str) -> PIIScanResult:
        """Use Rust-compiled regex via PyO3."""
        result = self._rust_module.scan_pii(text)
        redactions = [
            PIIMatch(type=m["type"], count=m["count"]) for m in result["matches"]
        ]
        flags = [f"PII_MASKED_{m.type}" for m in redactions]
        if not redactions:
            flags.append("PII_CLEAN")
        return PIIScanResult(
            masked=result["masked"], redactions=redactions, flags=flags
        )

    def _scan_python(self, text: str) -> PIIScanResult:
        """Pure Python fallback using compiled regex patterns."""
        masked = text
        redactions: list[PIIMatch] = []
        for pii_type, pattern in _PII_PATTERNS.items():
            matches = pattern.findall(masked)
            if matches:
                count = len(matches)
                masked = pattern.sub(_MASK_CHAR, masked)
                redactions.append(PIIMatch(type=pii_type, count=count))

        flags = [f"PII_MASKED_{r.type}" for r in redactions]
        if not redactions:
            flags.append("PII_CLEAN")

        return PIIScanResult(masked=masked, redactions=redactions, flags=flags)

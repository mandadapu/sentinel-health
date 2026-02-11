import re
from dataclasses import dataclass, field


@dataclass
class PHIMatch:
    type: str
    count: int


@dataclass
class PHIStripResult:
    cleaned: str
    redactions: list[PHIMatch] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


# Extended PHI patterns (superset of PII, includes clinical identifiers)
_PHI_PATTERNS: dict[str, re.Pattern] = {
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
    "PATIENT_NAME": re.compile(
        r"(?:Patient|Pt|patient|pt)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})"
    ),
    "PROVIDER_NAME": re.compile(
        r"(?:Dr\.|Dr|MD|NP|PA|RN)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})"
    ),
    "ADDRESS": re.compile(
        r"\b\d{1,5}\s(?:[A-Z][a-z]+\s){1,3}"
        r"(?:St|Ave|Blvd|Dr|Ln|Rd|Ct|Way|Pl)(?:\.|\b)"
    ),
}

_REDACT_TAG = "***PHI_REDACTED***"


class PHIStripper:
    def strip(self, text: str) -> PHIStripResult:
        cleaned = text
        redactions: list[PHIMatch] = []

        for phi_type, pattern in _PHI_PATTERNS.items():
            matches = pattern.findall(cleaned)
            if matches:
                count = len(matches)
                cleaned = pattern.sub(_REDACT_TAG, cleaned)
                redactions.append(PHIMatch(type=phi_type, count=count))

        flags = [f"PHI_STRIPPED_{r.type}" for r in redactions]
        if redactions:
            flags.insert(0, "PHI_REDACTED")
        else:
            flags.append("PHI_CLEAN")

        return PHIStripResult(cleaned=cleaned, redactions=redactions, flags=flags)

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema

logger = logging.getLogger(__name__)


@dataclass
class FHIRValidationResult:
    valid: bool
    flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FHIRValidator:
    def __init__(self, schema_dir: str = "schemas") -> None:
        self._schemas: dict[str, dict] = {}
        schema_path = Path(schema_dir)

        for node_name in ("extractor", "reasoner", "sentinel"):
            file_path = schema_path / f"{node_name}_output.json"
            if file_path.exists():
                with open(file_path) as f:
                    self._schemas[node_name] = json.load(f)
                logger.info("Loaded FHIR schema for %s", node_name)
            else:
                logger.warning("No FHIR schema found at %s", file_path)

    def validate(self, content: str, node_name: str) -> FHIRValidationResult:
        schema = self._schemas.get(node_name)
        if schema is None:
            return FHIRValidationResult(
                valid=True,
                flags=[f"FHIR_SCHEMA_MISSING_{node_name.upper()}"],
            )

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            return FHIRValidationResult(
                valid=False,
                flags=[f"FHIR_INVALID_{node_name.upper()}"],
                errors=[f"Invalid JSON: {e}"],
            )

        validator = jsonschema.Draft7Validator(schema)
        validation_errors = list(validator.iter_errors(data))

        if not validation_errors:
            return FHIRValidationResult(
                valid=True,
                flags=[f"FHIR_VALID_{node_name.upper()}"],
            )

        error_msgs = [
            f"{'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
            if e.absolute_path
            else e.message
            for e in validation_errors[:5]
        ]

        return FHIRValidationResult(
            valid=False,
            flags=[f"FHIR_INVALID_{node_name.upper()}"],
            errors=error_msgs,
        )

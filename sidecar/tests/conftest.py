import pytest

from src.config import SidecarSettings
from src.validators.fhir_validator import FHIRValidator
from src.validators.phi_stripper import PHIStripper
from src.validators.pii_scanner import PIIScanner
from src.validators.token_guard import TokenGuard


@pytest.fixture
def settings():
    return SidecarSettings(env="test", fhir_schema_dir="schemas")


@pytest.fixture
def pii_scanner():
    return PIIScanner(backend="python")


@pytest.fixture
def fhir_validator():
    return FHIRValidator(schema_dir="schemas")


@pytest.fixture
def phi_stripper():
    return PHIStripper()


@pytest.fixture
def token_guard(settings):
    return TokenGuard(settings)

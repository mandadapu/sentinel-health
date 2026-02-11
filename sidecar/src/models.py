from pydantic import BaseModel, Field


class TokenInfo(BaseModel):
    in_tokens: int = Field(alias="in", default=0)
    out_tokens: int = Field(alias="out", default=0)

    model_config = {"populate_by_name": True}


class ValidationRequest(BaseModel):
    content: str
    node_name: str = Field(pattern=r"^(extractor|reasoner|sentinel)$")
    encounter_id: str
    validation_type: str = Field(pattern=r"^(input|output|audit)$")
    tokens: TokenInfo = Field(default_factory=lambda: TokenInfo(**{"in": 0, "out": 0}))


class Redaction(BaseModel):
    type: str
    count: int


class ValidationResponse(BaseModel):
    validated: bool
    content: str
    compliance_flags: list[str] = Field(default_factory=list)
    redactions: list[Redaction] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    should_retry: bool = False
    latency_ms: float = 0.0

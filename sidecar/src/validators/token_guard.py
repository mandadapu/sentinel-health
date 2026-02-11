from dataclasses import dataclass, field

from src.config import SidecarSettings
from src.models import TokenInfo


@dataclass
class TokenGuardResult:
    flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TokenGuard:
    def __init__(self, settings: SidecarSettings) -> None:
        self._min_out = settings.min_output_tokens
        self._max_out = settings.max_output_tokens
        self._min_in = settings.min_input_tokens
        self._max_in = settings.max_input_tokens

    def check(self, tokens: TokenInfo, validation_type: str) -> TokenGuardResult:
        flags: list[str] = []
        errors: list[str] = []

        if validation_type == "input":
            in_count = tokens.in_tokens
            if in_count < self._min_in:
                flags.append("TOKEN_INPUT_SUSPICIOUSLY_SHORT")
                errors.append(
                    f"Input tokens ({in_count}) below minimum ({self._min_in})"
                )
            elif in_count > self._max_in:
                flags.append("TOKEN_INPUT_SUSPICIOUSLY_LONG")
                errors.append(
                    f"Input tokens ({in_count}) above maximum ({self._max_in})"
                )
            else:
                flags.append("TOKEN_INPUT_OK")

        elif validation_type == "output":
            out_count = tokens.out_tokens
            if out_count < self._min_out:
                flags.append("TOKEN_OUTPUT_SUSPICIOUSLY_SHORT")
                errors.append(
                    f"Output tokens ({out_count}) below minimum ({self._min_out})"
                )
            elif out_count > self._max_out:
                flags.append("TOKEN_OUTPUT_SUSPICIOUSLY_LONG")
                errors.append(
                    f"Output tokens ({out_count}) above maximum ({self._max_out})"
                )
            else:
                flags.append("TOKEN_OUTPUT_OK")

        return TokenGuardResult(flags=flags, errors=errors)

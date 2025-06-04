from enum import Enum

from infrastructure.prompts.tokens import COMPLEX_ANALYZE, HISTORICAL_PRICE_ANALYZE


class PromptMapper(Enum):
    HISTORICAL_PRICE_ANALYZE: str = HISTORICAL_PRICE_ANALYZE
    COMPLEX_ANALYZE: str = COMPLEX_ANALYZE

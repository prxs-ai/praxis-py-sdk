from enum import Enum
from infrastructure.prompts.tokens import HISTORICAL_PRICE_ANALYZE


class PromptMapper(Enum):
    HISTORICAL_PRICE_ANALYZE: str = HISTORICAL_PRICE_ANALYZE
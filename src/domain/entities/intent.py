from enum import Enum
from dataclasses import dataclass
from typing import Optional

class IntentCategory(str, Enum):
    GREETING = "GREETING"
    INSTITUTIONAL = "INSTITUTIONAL"
    MOVIE_SEARCH = "MOVIE_SEARCH"
    UNKNOWN = "UNKNOWN"

@dataclass
class IntentResult:
    category: IntentCategory
    confidence: float
    reasoning: Optional[str] = None

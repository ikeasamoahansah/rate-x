from abc import ABC, abstractmethod
from typing import Dict, Any
from ..core.request import RateLimitRequest
from ..core.response import RateLimitResponse


class RateLimitingAlgorithm(ABC):
    @abstractmethod
    async def allow_request(self, request: RateLimitRequest) -> RateLimitResponse:
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        pass

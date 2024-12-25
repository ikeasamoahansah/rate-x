from typing import Dict, Optional


class RateLimitResponse:
    def __init__(
        self,
        is_allowed: bool,
        headers: Dict[str, str] = None,
        retry_after: Optional[int] = None,
    ):
        self.is_allowed = is_allowed
        self.headers = headers or {}
        self.retry_after = retry_after

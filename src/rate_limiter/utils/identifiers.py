from typing import Callable
from ..core.request import RateLimitRequest

def default_identifier(request: RateLimitRequest) -> str:
    """Default request identifier using IP and path"""
    return f"{request.client_ip}:{request.path}"

def create_identifier(
    ip_based: bool = True,
    path_based: bool = True,
    method_based: bool = False
) -> Callable[[RateLimitRequest], str]:
    """Create a custom request identifier function"""
    def identifier(request: RateLimitRequest) -> str:
        parts = []
        if ip_based:
            parts.append(request.client_ip)
        if path_based:
            parts.append(request.path)
        if method_based:
            parts.append(request.method)
        return ":".join(parts)
    return identifier
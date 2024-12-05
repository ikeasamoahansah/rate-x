from typing import Optional, Dict, Any, Callable, Awaitable, Union
from dataclasses import dataclass
from time import time

import threading

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import asyncio
from functools import wraps

from ..core.request import RateLimitRequest
from ..core.response import RateLimitResponse

from ..algorithms.base import RateLimitingAlgorithm


class HTTPRateLimiter(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(
        self,
        app: FastAPI,
        algorithm: RateLimitingAlgorithm,
        status_code: int = 429,
        error_message: str = "Too Many Requests"
    ):
        super().__init__(app)
        self.algorithm = algorithm
        self.status_code = status_code
        self.error_message = error_message
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'rejected_requests': 0
        }
        self._lock = asyncio.Lock()

    def get_request_identifier(self, request: Request) -> str:
        """
        Generate a unique identifier for the request.
        Override this method to customize how requests are identified.
        """
        return f"{request.client.host}:{request.url.path}"

    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        async with self._lock:
            return {
                **self.stats,
                'algorithm_status': await self.algorithm.get_status()
            }

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process each request through the rate limiter"""
        
        # Create rate limit request object
        rate_limit_request = RateLimitRequest(
            id=self.get_request_identifier(request),
            timestamp=time(),
            client_ip=request.client.host,
            path=request.url.path,
            method=request.method,
            metadata={
                'headers': dict(request.headers),
                'query_params': dict(request.query_params)
            }
        )

        # Update stats
        async with self._lock:
            self.stats['total_requests'] += 1

        # Check if request is allowed
        rate_limit_response = await self.algorithm.allow_request(rate_limit_request)

        if rate_limit_response.is_allowed:
            # Update stats
            async with self._lock:
                self.stats['allowed_requests'] += 1

            # Process the request
            response = await call_next(request)

            # Add rate limit headers to response
            for header, value in rate_limit_response.headers.items():
                response.headers[header] = str(value)

            return response
        else:
            # Update stats
            async with self._lock:
                self.stats['rejected_requests'] += 1

            # Create error response
            headers = rate_limit_response.headers
            if rate_limit_response.retry_after:
                headers['Retry-After'] = str(rate_limit_response.retry_after)

            return JSONResponse(
                status_code=self.status_code,
                content={"error": self.error_message},
                headers=headers
            )

def rate_limit(algorithm: RateLimitingAlgorithm):
    """
    Decorator for rate limiting individual endpoints
    Usage:
        @app.get("/")
        @rate_limit(your_algorithm)
        async def endpoint():
            return {"message": "Hello World"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[0]
            if not isinstance(request, Request):
                raise ValueError("No request object found")

            rate_limit_request = RateLimitRequest(
                id=str(request.client.host),
                timestamp=time(),
                client_ip=request.client.host,
                path=request.url.path,
                method=request.method
            )

            response = await algorithm.allow_request(rate_limit_request)
            if not response.is_allowed:
                headers = response.headers
                if response.retry_after:
                    headers['Retry-After'] = str(response.retry_after)
                    
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too Many Requests"},
                    headers=headers
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
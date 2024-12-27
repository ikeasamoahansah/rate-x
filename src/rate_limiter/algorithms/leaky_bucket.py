import asyncio
from collections import deque
from time import time
from typing import Dict, Any, Optional

from src.rate_limiter.algorithms.base import RateLimitingAlgorithm
from src.rate_limiter.core.request import RateLimitRequest
from src.rate_limiter.core.response import RateLimitResponse


class LeakyBucketAlgorithm(RateLimitingAlgorithm):
    def __init__(self, bucket_size: int, leak_rate: float):
        """
        Initialize leaky bucket algorithm

        Args:
            bucket_size: Maximum number of requests the bucket can hold
            leak_rate: Number of requests processed per second
        """
        self.bucket_size = bucket_size
        self.leak_rate = leak_rate
        self.processing_interval = 1.0 / leak_rate

        self.bucket: deque = deque(maxlen=bucket_size)
        self.lock = asyncio.Lock()

        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.last_leak_time = time()
        self.processing_times: deque = deque(maxlen=1000)

        self.leak_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background leaking process"""
        if self.leak_task is None:
            self.leak_task = asyncio.create_task(self._leak_bucket())

    async def stop(self):
        """Stop the background leaking process"""
        if self.leak_task:
            self.leak_task.cancel()
            try:
                await self.leak_task
            except asyncio.CancelledError:
                pass
            self.leak_task = None

    async def _leak_bucket(self):
        """Background task that processes requests at the specified rate"""
        while True:
            await asyncio.sleep(self.processing_interval)
            async with self.lock:
                if self.bucket:
                    request = self.bucket.popleft()
                    process_time = time() - request.timestamp
                    self.processing_times.append(process_time)

    async def allow_request(self, request: RateLimitRequest) -> RateLimitResponse:
        """
        Determine if a new request should be allowed based on current bucket state

        Args:
            request: The incoming rate limit request

        Returns:
            RateLimitResponse indicating if request is allowed and relevant headers
        """
        self.total_requests += 1
        current_time = time()

        async with self.lock:
            current_size = len(self.bucket)

            if current_size < self.bucket_size:
                self.bucket.append(request)
                self.accepted_requests += 1

                headers = {
                    "X-RateLimit-Limit": str(self.bucket_size),
                    "X-RateLimit-Remaining": str(self.bucket_size - current_size - 1),
                    "X-RateLimit-Reset": str(
                        int(
                            current_time + (current_size + 1) * self.processing_interval
                        )
                    ),
                }

                return RateLimitResponse(is_allowed=True, headers=headers)
            else:
                self.rejected_requests += 1

                retry_after = int(current_size * self.processing_interval)

                headers = {
                    "X-RateLimit-Limit": str(self.bucket_size),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + retry_after)),
                    "Retry-After": str(retry_after),
                }

                return RateLimitResponse(
                    is_allowed=False, headers=headers, retry_after=retry_after
                )

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current algorithm status and metrics

        Returns:
            Dictionary containing current status and performance metrics
        """
        async with self.lock:
            current_size = len(self.bucket)
            avg_processing_time = (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times
                else 0
            )

            return {
                "config": {
                    "bucket_size": self.bucket_size,
                    "leak_rate": self.leak_rate,
                    "processing_interval": self.processing_interval,
                },
                "current_state": {
                    "current_size": current_size,
                    "utilization": current_size / self.bucket_size,
                },
                "metrics": {
                    "total_requests": self.total_requests,
                    "accepted_requests": self.accepted_requests,
                    "rejected_requests": self.rejected_requests,
                    "acceptance_rate": (
                        self.accepted_requests / self.total_requests
                        if self.total_requests > 0
                        else 0
                    ),
                    "avg_processing_time": avg_processing_time,
                },
            }

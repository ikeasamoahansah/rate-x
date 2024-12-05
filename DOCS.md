# HTTP Rate Limiter

A flexible and extensible HTTP rate limiting framework for Python web applications.

## Features

- Pluggable rate limiting algorithms
- FastAPI and Flask support
- Async support
- Customizable request identification
- HTTP header handling
- Statistics tracking

## Quick Start

```python
from fastapi import FastAPI
from rate_limiter.middleware import HTTPRateLimiter
from rate_limiter.algorithms import TokenBucketAlgorithm

app = FastAPI()
limiter = TokenBucketAlgorithm(bucket_size=100, refill_rate=10)
app.add_middleware(HTTPRateLimiter, algorithm=limiter)
```

## Documentation

See the `examples/` directory for usage examples with different web frameworks

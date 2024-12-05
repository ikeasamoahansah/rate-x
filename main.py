from fastapi import FastAPI
from src.rate_limiter.middleware.middleware import HTTPRateLimiter
# from src.rate_limiter.algorithms import TokenBucketAlgorithm

app = FastAPI()
# limiter = TokenBucketAlgorithm(bucket_size=100, refill_rate=10)
app.add_middleware(HTTPRateLimiter, algorithm=None)

# Continue other server related stuff here (this comment wasnt done by AI)
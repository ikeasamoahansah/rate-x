# rate-x
A simple rate limiter


## TODO:

- Functional Requirements:
    - limit calls to API
    - eg. 2 requests/second
    - how to display to user

- Non functional Requirements:
    - what kind (client side, server, middleware)
    - is high availability required?
    - pitfalls? performance?
    - should be fast and use little memory
    - should placed in between client and server

- Data Modelling:
    - which database
    - mysql (relational) not optimal, too slow.
    - redis is better

### Algorithms

- Leaking Bucket:
    - can start by implementing this algo
    - it uses a queue based system FIFO
    - parameters(bucket_size, process_rate)
    - memory efficient, stable processing -> advantages
    - weak support for burst traffic, parameters difficult to get right -> disadv


- Token Bucket:
    - similar to leaking bucket but uses token
    - dynamic rate of processing
    - predefined capacity
    - parameters(bucket_size, refill_rate)
    - buckets needed depends on our needs
    - bets to have diff buckets for every endpoint
    - tiny memory usage, allows burst of traffic -> pros
    - parameters difficult to adjust -> cons


- Fixed Window:
    - divides timeline into fixed sized windows
    - easy to implement, small memory -> pros
    - not accurate because more requests can go through -> cons



- Sliding Window:
    - assumes a constant rate of requests
    - good enough accuracy, memory eff, no starvation problem -> pros
    - not exactly accurate -> cons


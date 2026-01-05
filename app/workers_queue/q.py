import os
from redis import Redis
from rq import Queue

redis_connection = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    socket_connect_timeout=5,
    socket_timeout=5,
)
q = Queue(connection=redis_connection)
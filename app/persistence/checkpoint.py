
from contextlib import contextmanager

from langgraph.checkpoint.redis import RedisSaver

from app.config import get_settings

@contextmanager
def redis_checkpointer():
    settings = get_settings()

    with RedisSaver.from_conn_string(
        settings.redis_url
    ) as saver:
        saver.setup()

        yield saver
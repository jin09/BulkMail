from redis import Redis

from conf import REDIS_HOST


class RedisClient:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls.connection = Redis(host=REDIS_HOST)
        return cls._instance

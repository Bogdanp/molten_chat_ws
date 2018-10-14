from molten import Settings
from redis import StrictRedis as Redis


class RedisComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is Redis

    def resolve(self, settings: Settings):
        return Redis.from_url(settings.strict_get("redis.url"))

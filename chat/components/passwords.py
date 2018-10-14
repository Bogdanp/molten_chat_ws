from molten import Settings
from passlib.context import CryptContext


class PasswordHasher:
    __slots__ = ["context"]

    def __init__(self, settings):
        self.context = CryptContext(**settings.deep_get("passwords", default={}))

    def check(self, password_hash, password):
        return self.context.verify(password, password_hash)

    def hash(self, password):
        return self.context.encrypt(password)


class PasswordHasherComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is PasswordHasher

    def resolve(self, settings: Settings):
        return PasswordHasher(settings)

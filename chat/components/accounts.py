from molten.contrib.sessions import Session
from molten.contrib.sqlalchemy import Session as DBSession
from molten.typing import extract_optional_annotation
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import IntegrityError

from ..models import Manager, Model
from .passwords import PasswordHasher


class Account(Model):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    username = Column(String, index=True, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class AccountError(Exception):
    pass


class UsernameTaken(AccountError):
    pass


class AccountManager(Manager):
    __slots__ = ["password_hasher", "session"]

    def __init__(self, password_hasher: PasswordHasher, session: DBSession):
        self.password_hasher = password_hasher
        self.session = session

    def create(self, username, password):
        try:
            account = Account(username=username)
            account.password_hash = self.password_hasher.hash(password)
            self.session.add(account)
            self.session.flush()
            return account
        except IntegrityError:
            raise UsernameTaken()

    def find_by_id(self, id):
        return self.session.query(Account).get(id)

    def find_by_username(self, username):
        return self.session.query(Account).filter_by(username=username).first()

    def find_by_username_and_password(self, username, password):
        account = self.find_by_username(username)
        if not account or not self.password_hasher.check(account.password_hash, password):
            return None

        return account


class AccountManagerComponent:
    is_cacheable = True
    is_singleton = False

    def can_handle_parameter(self, parameter):
        return parameter.annotation is AccountManager

    def resolve(self, password_hasher: PasswordHasher, session: DBSession):
        return AccountManager(password_hasher, session)


class CurrentAccountComponent:
    is_cacheable = True
    is_singleton = False

    def can_handle_parameter(self, parameter):
        _, annotation = extract_optional_annotation(parameter.annotation)
        return annotation is Account

    def resolve(self, account_manager: AccountManager, session: Session):
        account_id = session.get("account_id")
        if not account_id:
            return None

        return account_manager.find_by_id(account_id)

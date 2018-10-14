from molten import HTTP_400, HTTPError, Route, schema
from molten.contrib.sessions import Session

from ..components.accounts import AccountManager


@schema
class SessionData:
    username: str
    password: str


def create_session(session: Session, session_data: SessionData, account_manager: AccountManager):
    account = account_manager.find_by_username_and_password(session_data.username, session_data.password)
    if not account:
        raise HTTPError(HTTP_400, {"errors": {"username": "invalid username or password"}})

    session["account_id"] = account.id
    return {}


routes = [
    Route("", create_session, method="POST")
]

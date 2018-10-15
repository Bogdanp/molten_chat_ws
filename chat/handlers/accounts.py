from typing import Optional

from molten import HTTP_400, HTTPError, Route, field, schema

from ..common import schema_from_model
from ..components.accounts import AccountManager, UsernameTaken


@schema
class AccountData:
    id: Optional[int] = field(response_only=True)
    username: str = field(min_length=6)
    password: str = field(min_length=6, request_only=True)


def create_account(account_data: AccountData, account_manager: AccountManager) -> AccountData:
    try:
        account = account_manager.create(account_data.username, account_data.password)
        return schema_from_model(AccountData, account)
    except UsernameTaken:
        raise HTTPError(HTTP_400, {"errors": {"username": "this username is taken"}})


routes = [
    Route("", create_account, method="POST"),
]

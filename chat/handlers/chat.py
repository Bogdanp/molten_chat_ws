import logging
from typing import Optional

from molten import HTTP_403, HTTPError, Route, annotate
from molten.contrib.sqlalchemy import Session
from molten.contrib.websockets import Websocket

from ..components.accounts import Account
from ..components.chatrooms import ChatHandlerFactory

LOGGER = logging.getLogger(__name__)


@annotate(supports_ws=True)
def chat(account: Optional[Account], handler_factory: ChatHandlerFactory, session: Session, socket: Websocket):
    if not account:
        raise HTTPError(HTTP_403, {"errors": "forbidden"})

    # Grab the username and close the DB session to avoid starvation.
    username = account.username
    session.close()

    handler = handler_factory(socket, username)
    handler.handle_until_close()


routes = [
    Route("", chat)
]

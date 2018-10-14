import json
import logging
from typing import Optional

from gevent import Timeout
from molten import HTTP_403, HTTPError, Route, annotate
from molten.contrib.websockets import CloseMessage, Websocket

from ..components.accounts import Account
from ..components.chatrooms import ChatroomManager

LOGGER = logging.getLogger(__name__)


@annotate(supports_ws=True)
def chat(account: Optional[Account], chatrooms: ChatroomManager, sock: Websocket):
    if not account:
        raise HTTPError(HTTP_403, {"errors": "forbidden"})

    try:
        username = account.username
        while not sock.closed:
            try:
                message = sock.receive(timeout=1)
            except Timeout:
                continue

            if isinstance(message, CloseMessage):
                break

            event = json.loads(message.get_text())
            try:
                action = getattr(chatrooms, f"on_{event.pop('type')}")
                action(sock, username, **event)
            except Exception:
                LOGGER.exception("Failed to handle event: %r", event)
                continue
    finally:
        chatrooms.on_close(sock, username)


routes = [
    Route("", chat)
]

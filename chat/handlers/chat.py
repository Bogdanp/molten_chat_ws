import json
from queue import Empty, Queue
from threading import Lock
from typing import Optional

import gevent
from gevent import Timeout
from molten import HTTP_403, HTTPError, Route, annotate
from molten.contrib.websockets import CloseMessage, TextMessage, Websocket

from ..components.accounts import Account

CHATROOMS = {}
CHATROOM_MUTEX = Lock()


def JsonMessage(**kwargs):
    return TextMessage(json.dumps(kwargs))


class ChatroomHandler:
    def __init__(self, members, events):
        self.members = members
        self.events = events
        self.running = True

    def stop(self):
        self.running = False

    def on_join(self, subject):
        message = JsonMessage(type="join", username=subject)
        for member, username in self.members.items():
            member.send(message)

    def on_broadcast(self, subject, message):
        message = JsonMessage(type="broadcast", username=subject, message=message)
        for member, username in self.members.items():
            member.send(message)

    def on_leave(self, subject):
        message = JsonMessage(type="leave", username=subject)
        for member, username in self.members.items():
            member.send(message)

    def __call__(self):
        while self.running:
            try:
                event = self.events.get(timeout=1)
                getattr(self, f"on_{event.pop('type')}")(**event)
            except Empty:
                continue


class Chatroom:
    def __init__(self):
        self.messages = Queue()
        self.members = {}
        self.events = Queue()
        self.handler = gevent.spawn(ChatroomHandler(self.members, self.events))

    def add_member(self, sock, username):
        self.members[sock] = username
        sock.send(JsonMessage(type="present", members=list(self.members.values())))
        self.events.put({"type": "join", "subject": username})

    def remove_member(self, sock, username):
        del self.members[sock]
        self.events.put({"type": "leave", "subject": username})

    def broadcast(self, sock, username, message):
        self.events.put({"type": "broadcast", "subject": username, "message": message})


class ChatHandler:
    def __init__(self, sock, username):
        self.sock = sock
        self.username = username
        self.chatrooms = set()

    def get_chatroom(self, room_name):
        try:
            chatroom = CHATROOMS[room_name]
        except KeyError:
            with CHATROOM_MUTEX:
                chatroom = CHATROOMS.get(room_name)
                if not chatroom:
                    CHATROOMS[room_name] = chatroom = Chatroom()

        self.chatrooms.add(chatroom)
        return chatroom

    def on_open(self):
        pass

    def on_join(self, room_name):
        chatroom = self.get_chatroom(room_name)
        chatroom.add_member(self.sock, self.username)

    def on_message(self, room_name, message):
        chatroom = self.get_chatroom(room_name)
        chatroom.broadcast(self.sock, self.username, message)

    def on_close(self):
        for chatroom in self.chatrooms:
            chatroom.remove_member(self.sock, self.username)


@annotate(supports_ws=True)
def chat(account: Optional[Account], sock: Websocket):
    if not account:
        raise HTTPError(HTTP_403, {"errors": "forbidden"})

    try:
        handler = ChatHandler(sock, account.username)
        handler.on_open()
        while not sock.closed:
            try:
                message = sock.receive(timeout=1)
            except Timeout:
                continue

            if isinstance(message, CloseMessage):
                break

            event = json.loads(message.get_text())
            try:
                action = getattr(handler, f"on_{event.pop('type')}")
                action(**event)
            except AttributeError:
                continue

    finally:
        handler.on_close()


routes = [
    Route("", chat)
]

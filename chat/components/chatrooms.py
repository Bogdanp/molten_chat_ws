import json
import logging
from collections import defaultdict

import gevent
from molten.contrib.websockets import TextMessage

from .redis import Redis

LOGGER = logging.getLogger(__name__)


def JsonMessage(**kwargs):
    return TextMessage(json.dumps(kwargs))


class ChatroomListener:
    def __init__(self, redis, manager):
        self.redis = redis
        self.manager = manager

    def __call__(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe("chat:events")
        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        handler = getattr(self.manager, f"handle_{event['type']}")
                        handler(*event["args"])
                    except Exception:
                        LOGGER.exception("Failed to handle event: %r", event)
        finally:
            pubsub.close()


class ChatroomManager:
    def __init__(self, redis):
        self.redis = redis
        self.sockets_by_room = defaultdict(dict)
        self.rooms_by_socket = defaultdict(set)
        self.listener = ChatroomListener(redis, self)
        self.listener_greenlet = gevent.spawn(self.listener)

    def _dispatch(self, type, *args):
        self.redis.publish("chat:events", json.dumps({
            "type": type,
            "args": args,
        }))

    # The following methods are called by users of this class.

    def on_join(self, socket, username, room_name):
        self.sockets_by_room[room_name][socket] = username
        self.rooms_by_socket[socket].add(room_name)
        self._dispatch("join", room_name, username)

    def on_leave(self, socket, username, room_name):
        try:
            del self.sockets_by_room[room_name][socket]
            self._dispatch("leave", room_name, username)
        except KeyError:
            pass

    def on_message(self, socket, username, room_name, message):
        self._dispatch("broadcast", room_name, username, message)

    def on_close(self, socket, username):
        for room_name in self.rooms_by_socket[socket]:
            username = self.sockets_by_room[room_name].pop(socket)
            self._dispatch("leave", room_name, username)

    # The following methods are called by ChatroomListener when a
    # message comes in via Redis.

    def handle_join(self, room, username):
        for sock in self.sockets_by_room[room]:
            sock.send(JsonMessage(type="join", username=username))

    def handle_leave(self, room, username):
        for sock in self.sockets_by_room[room]:
            sock.send(JsonMessage(type="leave", username=username))

    def handle_broadcast(self, room, username, message):
        for sock in self.sockets_by_room[room]:
            sock.send(JsonMessage(type="broadcast", username=username, message=message))


class ChatroomManagerComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is ChatroomManager

    def resolve(self, redis: Redis):
        return ChatroomManager(redis)

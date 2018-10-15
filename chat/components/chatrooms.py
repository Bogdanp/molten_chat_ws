import json
import logging
import time
from collections import defaultdict
from functools import partial
from threading import Lock

import gevent
from gevent import Timeout
from molten.contrib.websockets import CloseMessage, TextMessage

from .redis import Redis

LOGGER = logging.getLogger(__name__)


def JsonMessage(**kwargs):
    return TextMessage(json.dumps(kwargs))


class ChatroomRegistry:
    def __init__(self, redis):
        self.redis = redis
        self.sockets_mutex = Lock()
        self.sockets_by_room = defaultdict(dict)
        self.rooms_by_socket = defaultdict(set)

    def touch_member(self, room_name, username):
        self.redis.zadd(f"chat:rooms:{room_name}", int(time.time()), username)

    def add_member_to_room(self, room_name, socket, username):
        self.touch_member(room_name, username)
        with self.sockets_mutex:
            self.sockets_by_room[room_name][socket] = username
            self.rooms_by_socket[socket].add(room_name)

    def remove_member_from_room(self, room_name, socket):
        username = self.sockets_by_room[room_name][socket]
        self.redis.zrem(f"chat:rooms:{room_name}", username)
        with self.sockets_mutex:
            try:
                del self.sockets_by_room[room_name][socket]
                self.rooms_by_socket[socket].remove(room_name)
            except KeyError:
                pass

    def remove_member_from_all_rooms(self, socket):
        with self.sockets_mutex:
            room_names = list(self.rooms_by_socket[socket])
            for room_name in room_names:
                try:
                    del self.sockets_by_room[socket]
                except KeyError:
                    continue

            del self.rooms_by_socket[socket]
            return room_names

    def get_members(self, room_name):
        members = self.redis.zrangebyscore(f"chat:rooms:{room_name}", int(time.time() - 60), "+inf")
        return sorted(username.decode() for username in members)

    def get_sockets(self, room_name):
        return list(self.sockets_by_room[room_name])

    def send_to_all(self, room_name, message):
        for socket in self.get_sockets(room_name):
            try:
                socket.send(message)
            except Exception as e:
                LOGGER.warning(".send() failed on socket: %s", e)
                self.remove_member_from_room(room_name, socket)


class ChatroomRegistryComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is ChatroomRegistry

    def resolve(self, redis: Redis):
        return ChatroomRegistry(redis)


class ChatroomListener:
    def __init__(self, redis, registry):
        self.redis = redis
        self.registry = registry
        self.listener = gevent.spawn(self.listen)

    def listen(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe("chat:events")
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                event = json.loads(message["data"])
                handler = getattr(self, f"handle_{event['type']}")
                handler(*event["args"])
            except Exception:
                LOGGER.exception("Failed to handle event: %r", event)

    def handle_join(self, room_name, username):
        self.registry.send_to_all(room_name, JsonMessage(type="join", username=username))
        self.registry.send_to_all(room_name, JsonMessage(type="presence", usernames=self.registry.get_members(room_name)))

    def handle_leave(self, room_name, username):
        self.registry.send_to_all(room_name, JsonMessage(type="leave", username=username))
        self.registry.send_to_all(room_name, JsonMessage(type="presence", usernames=self.registry.get_members(room_name)))

    def handle_broadcast(self, room_name, username, message):
        self.registry.send_to_all(room_name, JsonMessage(type="broadcast", username=username, message=message))


class ChatroomListenerComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is ChatroomListener

    def resolve(self, redis: Redis, registry: ChatroomRegistry):
        return ChatroomListener(redis, registry)


class ChatHandlerFactory:
    def __init__(self, redis, registry, socket, username):
        self.redis = redis
        self.registry = registry
        self.socket = socket
        self.username = username

    def handle_until_close(self):
        try:
            while not self.socket.closed:
                try:
                    message = self.socket.receive(timeout=1)
                except Timeout:
                    continue

                if isinstance(message, CloseMessage):
                    return

                event = json.loads(message.get_text())
                try:
                    action = getattr(self, f"on_{event.pop('type')}")
                    action(**event)
                except Exception:
                    LOGGER.exception("Failed to handle event: %r", event)
                    continue
        finally:
            self.on_close()

    def dispatch_event(self, type, *args):
        self.redis.publish("chat:events", json.dumps({
            "type": type,
            "args": args,
        }))

    def on_close(self):
        room_names = self.registry.remove_member_from_all_rooms(self.socket)
        for room_name in room_names:
            self.dispatch_event("leave", room_name, self.username)

    def on_join(self, room_name):
        self.registry.add_member_to_room(room_name, self.socket, self.username)
        self.dispatch_event("join", room_name, self.username)

    def on_leave(self, room_name):
        self.registry.remove_member_from_room(room_name, self.socket)
        self.dispatch_event("leave", room_name, self.username)

    def on_ping(self, room_name):
        self.registry.touch_member(room_name, self.username)
        self.socket.send(JsonMessage(type="pong"))

    def on_message(self, room_name, message):
        self.registry.touch_member(room_name, self.username)
        self.dispatch_event("broadcast", room_name, self.username, message)


class ChatHandlerFactoryComponent:
    is_cacheable = True
    is_singleton = True

    def can_handle_parameter(self, parameter):
        return parameter.annotation is ChatHandlerFactory

    def resolve(self, redis: Redis, registry: ChatroomRegistry):
        return partial(ChatHandlerFactory, redis, registry)

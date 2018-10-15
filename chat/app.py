from typing import Optional

from molten import App, Include, ResponseRendererMiddleware, Route, SettingsComponent, redirect
from molten.contrib.request_id import RequestIdMiddleware
from molten.contrib.sessions import CookieStore, SessionComponent, SessionMiddleware
from molten.contrib.sqlalchemy import SQLAlchemyEngineComponent, SQLAlchemyMiddleware, SQLAlchemySessionComponent
from molten.contrib.templates import Templates, TemplatesComponent
from molten.contrib.websockets import WebsocketsMiddleware
from molten.openapi import Metadata, OpenAPIHandler, OpenAPIUIHandler
from whitenoise import WhiteNoise

from . import settings
from .common import path_to
from .components.accounts import Account, AccountManagerComponent, CurrentAccountComponent
from .components.chatrooms import ChatHandlerFactoryComponent, ChatroomListenerComponent, ChatroomRegistryComponent
from .components.passwords import PasswordHasherComponent
from .components.redis import RedisComponent
from .handlers import accounts, chat, sessions
from .logging import setup_logging


def index(account: Optional[Account], templates: Templates):
    if not account:
        return redirect("/login")
    return templates.render("index.html")


def login(templates: Templates):
    return templates.render("login.html")


def register(templates: Templates):
    return templates.render("register.html")


def setup_app():
    setup_logging()

    cookie_store = CookieStore(**settings.strict_get("sessions"))

    get_schema = OpenAPIHandler(
        Metadata(
            title="Chat",
            description="A simple chat app.",
            version="0.0.0",
        ),
    )

    get_docs = OpenAPIUIHandler()

    app = App(
        components=[
            AccountManagerComponent(),
            ChatHandlerFactoryComponent(),
            ChatroomListenerComponent(),
            ChatroomRegistryComponent(),
            CurrentAccountComponent(),
            PasswordHasherComponent(),
            RedisComponent(),
            SQLAlchemyEngineComponent(),
            SQLAlchemySessionComponent(),
            SessionComponent(cookie_store),
            SettingsComponent(settings),
            TemplatesComponent(path_to("templates")),
        ],

        middleware=[
            RequestIdMiddleware(),
            SessionMiddleware(cookie_store),
            ResponseRendererMiddleware(),
            WebsocketsMiddleware(),
            SQLAlchemyMiddleware(),
        ],

        routes=[
            Route("/_schema", get_schema),
            Route("/_docs", get_docs),
            Route("/", index),
            Route("/login", login),
            Route("/register", register),

            Include("/v1", [
                Include("/accounts", accounts.routes, namespace="accounts"),
                Include("/chat", chat.routes, namespace="chat"),
                Include("/sessions", sessions.routes, namespace="sessions"),
            ], namespace="v1"),
        ],
    )

    decorated_app = WhiteNoise(app, **settings.strict_get("whitenoise"))
    return decorated_app, app

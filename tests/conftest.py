import gevent.monkey; gevent.monkey.patch_all()  # noqa isort: ignore

import base64

import pytest
from molten import testing
from molten.contrib.sqlalchemy import Session
from molten.contrib.websockets import WebsocketsTestClient

from chat.app import setup_app
from chat.components.accounts import AccountManager
from chat.components.redis import Redis


def truncate_all_tables(session: Session):
    table_names = session.execute("""
        select table_name from information_schema.tables
        where table_schema = 'public'
        and table_type = 'BASE TABLE'
        and table_name != 'alembic_version'
    """)
    for (table_name,) in table_names:
        # "truncate" can deadlock so we use delete which is guaranteed not to.
        session.execute(f"delete from {table_name}")
    session.commit()


def flush_redis(redis: Redis):
    redis.flushall()


@pytest.fixture(scope="session")
def app_global():
    _, app = setup_app()
    return app


@pytest.fixture
def app(app_global):
    # This is a little "clever"/piggy. We only want a single instance
    # of the app to ever be created, but we also want to ensure that
    # the DB is cleared after every test hence "app_global" being a
    # session-scoped fixture and this one being test-scoped.
    yield app_global
    resolver = app_global.injector.get_resolver()
    resolver.resolve(truncate_all_tables)()
    resolver.resolve(flush_redis)()


@pytest.fixture
def client(app):
    return testing.TestClient(app)


@pytest.fixture
def client_ws(app):
    return WebsocketsTestClient(app)


@pytest.fixture
def load_component(app):
    def load(annotation):
        def loader(c: annotation):
            return c
        return app.injector.get_resolver().resolve(loader)()
    return load


@pytest.fixture
def account(load_component):
    account_manager = load_component(AccountManager)
    return account_manager.create("jim.gordon", "bruceisbatman")


@pytest.fixture
def account_auth(account):
    def auth(request):
        sequence = base64.urlsafe_b64encode(b"jim.gordon:bruceisbatman")
        request.headers["Authorization"] = f"Basic {sequence.decode()}"
        return request
    return auth


@pytest.fixture
def alt_account(load_component):
    account_manager = load_component(AccountManager)
    return account_manager.create("bruce.wayne", "jimisclueless")


@pytest.fixture
def alt_account_auth(alt_account):
    def auth(request):
        sequence = base64.urlsafe_b64encode(b"bruce.wayne:jimisclueless")
        request.headers["Authorization"] = f"Basic {sequence.decode()}"
        return request
    return auth

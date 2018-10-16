import json

from molten.contrib.websockets import TextMessage


def JsonMessage(*, type, **kwargs):
    return TextMessage(json.dumps({"type": type, **kwargs}))


def test_pings(app, account, account_auth, client_ws):
    def read_messages(n):
        return [json.loads(sock.receive(timeout=1).get_text()) for _ in range(n)]

    # Given that I have an account
    with client_ws.connect(app.reverse_uri("v1:chat:chat"), auth=account_auth) as sock:
        # When I send a Ping message
        sock.send(JsonMessage(type="join", room_name="general"))
        sock.send(JsonMessage(type="ping", room_name="general"))

        # Then I should get back a Pong message
        messages = read_messages(3)
        assert {"type": "pong"} in messages


def test_chat(app, account, account_auth, alt_account, alt_account_auth, client_ws):
    def read_messages(n):
        return [json.loads(sock.receive(timeout=1).get_text()) for _ in range(n)]

    account_username = "jim.gordon"
    alt_account_username = "bruce.wayne"

    # Given that I have an account
    with client_ws.connect(app.reverse_uri("v1:chat:chat"), auth=account_auth) as sock:
        # When I join the "general" chatroom
        sock.send(JsonMessage(type="join", room_name="general"))

        # Then I should get back a message saying that I joined
        # And another containing the list of users in the channel
        messages = read_messages(2)
        assert messages == [
            {"type": "join", "username": account_username},
            {"type": "presence", "usernames": [account_username]},
        ]

        # When someone else joins the chat
        with client_ws.connect(app.reverse_uri("v1:chat:chat"), auth=alt_account_auth) as alt_sock:
            alt_sock.send(JsonMessage(type="join", room_name="general"))

            # Then I should get messages notifying me that they joined
            messages = read_messages(2)
            assert messages == [
                {"type": "join", "username": alt_account_username},
                {"type": "presence", "usernames": sorted([account_username, alt_account_username])},
            ]

            # When they broadcast a message
            alt_sock.send(JsonMessage(type="message", room_name="general", message="Hello!"))

            # Then I should receive that message
            messages = read_messages(1)
            assert messages == [
                {"type": "broadcast", "username": alt_account_username, "message": "Hello!"}
            ]

            # When they leave the chat
            alt_sock.send(JsonMessage(type="leave", room_name="general"))

            # Then I should get messages notifying me that they left
            messages = read_messages(2)
            assert messages == [
                {"type": "leave", "username": alt_account_username},
                {"type": "presence", "usernames": [account_username]},
            ]

/* global $ */

const ESCAPES = {
  "&": "&amp",
  "<": "&lt",
  ">": "&gt",
  '"': "&quot",
  "'": "&#39"
};

function escape(s) {
  return s && s.replace(/[&<>"']/g, c => ESCAPES[c]);
}

function capitalize(s) {
  return s[0].toUpperCase() + s.slice(1);
}

function JsonMessage(data) {
  return JSON.stringify(data);
}

class ChatController {
  constructor(messagingController, membersController) {
    this.messagingController = messagingController;
    this.membersController = membersController;

    this.connect();
    this.pingInterval = window.setInterval(this.sendPing.bind(this), 10000);
    this.reconnectInterval = window.setInterval(
      this.reconnect.bind(this),
      3000
    );
  }

  connect() {
    const URI = window.location.origin.replace("http", "ws") + "/v1/chat";
    this.sock = new WebSocket(URI);
    this.sock.onopen = this.onSocketOpened.bind(this);
    this.sock.onclose = this.onSocketClosed.bind(this);
    this.sock.onerror = this.onSocketError.bind(this);
    this.sock.onmessage = this.onSocketMessage.bind(this);
  }

  reconnect() {
    if (this.sock.readyState === 3) {
      this.messagingController.addStatusMessage("Reconnecting...");
      this.connect();
    }
  }

  sendMessage(message) {
    this.sock.send(
      JsonMessage({ type: "message", room_name: this.currentRoom, message })
    );
  }

  sendPing() {
    if (this.sock.readyState === 1) {
      this.sock.send(
        JsonMessage({ type: "ping", room_name: this.currentRoom })
      );
    }
  }

  onRoomChanged(roomName) {
    this.currentRoom = roomName;
    this.sock.send(JsonMessage({ type: "join", room_name: roomName }));
  }

  onSocketOpened() {
    this.onRoomChanged("general");
    this.messagingController.addStatusMessage("You are connected.");
  }

  onSocketClosed() {
    this.messagingController.addStatusMessage("You have been disconnected.");
  }

  onSocketError() {}

  onSocketMessage(message) {
    const data = JSON.parse(message.data);
    this[`on${capitalize(data.type)}Event`](data);
  }

  onJoinEvent({ username }) {
    this.messagingController.addStatusMessage(
      `${username} has joined the room.`
    );
    this.membersController.addMember(username);
  }

  onLeaveEvent({ username }) {
    this.messagingController.addStatusMessage(`${username} has left the room.`);
    this.membersController.removeMember(username);
  }

  onPresenceEvent({ usernames }) {
    usernames.forEach(username => this.membersController.addMember(username));
  }

  onPongEvent() {}

  onBroadcastEvent({ username, message }) {
    this.messagingController.addMessage(username, message);
  }
}

class MessagingController {
  constructor($messages) {
    this.$messages = $messages;
  }

  addMessage(username, message) {
    const $el = $(
      `<li class="room-messages__message">
         <strong>${escape(username)}</strong>
         ${escape(message)}
       </li>`
    );
    this.$messages.append($el);
    this.scrollToBottom();
  }

  addStatusMessage(message) {
    const $el = $(
      `<li class="room-messages__message room-messages__message--status">
         ${escape(message)}
       </li>`
    );
    this.$messages.append($el);
    this.scrollToBottom();
  }

  scrollToBottom() {
    this.$messages.animate(
      { scrollTop: this.$messages.prop("scrollHeight") },
      500
    );
  }
}

class MembersController {
  constructor($members) {
    this.$members = $members;
    this.members = [];
  }

  addMember(username) {
    if (this.members.indexOf(username) === -1) {
      this.members.push(username);
    }

    this.render();
  }

  removeMember(username) {
    const idx = this.members.indexOf(username);
    if (idx !== -1) {
      this.members.splice(idx, 1);
    }

    this.render();
  }

  render() {
    this.$members.find("li").remove();

    this.members.forEach(member => {
      this.$members.append(
        $(`<li class="room-members__member">${escape(member)}</li>`)
      );
    });
  }
}

class MessageBarController {
  constructor($messageBar, chatController) {
    this.$messageBar = $messageBar;
    this.$messageBar.on("keydown", this.onKeyPressed.bind(this));

    this.chatController = chatController;
  }

  onKeyPressed(e) {
    if (e.keyCode === 13) {
      const message = e.target.value;
      if (message.trim() !== "") {
        e.target.value = "";
        this.chatController.sendMessage(message);
      }
    }
  }
}

window.ChatController = ChatController;
window.MessagingController = MessagingController;
window.MembersController = MembersController;
window.MessageBarController = MessageBarController;

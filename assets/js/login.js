/* global $ */

function login({ username, password }) {
  return $.ajax("/v1/sessions", {
    method: "POST",
    data: JSON.stringify({ username, password }),
    contentType: "application/json"
  });
}

class LoginController {
  constructor($form) {
    this.$form = $form;
    this.$form.on("submit", this.onFormSubmitted.bind(this));
  }

  onFormSubmitted(e) {
    e.preventDefault();

    const data = {};
    this.$form
      .serializeArray()
      .forEach(({ name, value }) => (data[name] = value));

    login(data)
      .then(() => {
        window.location.href = "/";
      })
      .fail(res => {
        console.error(res.responseJSON);
      });
  }
}

export default (window.LoginController = LoginController);

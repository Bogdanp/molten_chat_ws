/* global $ */

function register({ username, password }) {
  return $.ajax("/v1/accounts", {
    method: "POST",
    data: JSON.stringify({ username, password }),
    contentType: "application/json"
  });
}

class RegisterController {
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

    register(data)
      .then(() => {
        window.location.href = "/login";
      })
      .fail(res => {
        console.error(res.responseJSON);
      });
  }
}

export default (window.RegisterController = RegisterController);

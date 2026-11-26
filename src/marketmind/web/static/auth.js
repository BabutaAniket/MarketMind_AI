"use strict";

const form = document.getElementById("auth-form");
const message = document.getElementById("auth-message");
const submit = document.getElementById("auth-submit");
const password = form.elements.password;
let mode = "login";

function chooseMode(nextMode) {
  mode = nextMode;
  const registering = mode === "register";
  document.getElementById("show-login").classList.toggle("selected", !registering);
  document.getElementById("show-register").classList.toggle("selected", registering);
  submit.textContent = registering ? "Create account" : "Sign in";
  password.autocomplete = registering ? "new-password" : "current-password";
  password.minLength = registering ? 12 : 1;
  document.getElementById("password-hint").hidden = !registering;
  message.textContent = "";
  message.className = "auth-message";
}

document.getElementById("show-login").addEventListener("click", () => chooseMode("login"));
document.getElementById("show-register").addEventListener("click", () => chooseMode("register"));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submit.disabled = true;
  message.textContent = "";
  message.className = "auth-message";
  try {
    const response = await fetch(`/api/auth/${mode === "register" ? "register" : "login"}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not sign in.");
    window.location.assign("/");
  } catch (error) {
    message.textContent = error.message || "Could not connect. Please try again.";
    message.classList.add("error");
  } finally {
    submit.disabled = false;
  }
});

chooseMode("login");

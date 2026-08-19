document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("login-message");
  msg.textContent = "";
  msg.className = "message";

  try {
    const data = await InsightBot.api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value.trim(),
        password: form.password.value,
      }),
    });
    InsightBot.setSession(data.access_token, data.user);
    window.location.href = "/";
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "message error";
  }
});

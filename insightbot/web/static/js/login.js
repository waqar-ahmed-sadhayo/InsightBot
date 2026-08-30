(() => {
  const toggleBtn = document.getElementById("toggle-password-btn");
  const passwordInput = document.getElementById("login-password");
  if (!toggleBtn || !passwordInput) return;
  toggleBtn.addEventListener("click", () => {
    const showing = passwordInput.type === "text";
    passwordInput.type = showing ? "password" : "text";
    toggleBtn.querySelector(".material-symbols-outlined").textContent = showing ? "visibility" : "visibility_off";
    toggleBtn.title = showing ? "Show password" : "Hide password";
    toggleBtn.setAttribute("aria-label", toggleBtn.title);
  });
})();

document.querySelectorAll(".demo-copy-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(btn.dataset.copy);
      const icon = btn.querySelector(".material-symbols-outlined");
      icon.textContent = "check";
      setTimeout(() => { icon.textContent = "content_copy"; }, 1200);
    } catch (err) {
      InsightBot.toast("Could not copy", "error");
    }
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("login-message");
  msg.textContent = "";
  msg.className = "font-body-md text-body-md mt-4";

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
    msg.className = "font-body-md text-body-md mt-4 font-medium text-red-600 dark:text-rose-300";
  }
});

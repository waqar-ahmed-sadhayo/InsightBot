document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("register-message");
  msg.textContent = "";
  msg.className = "font-body-md text-body-md mt-4";
  msg.style.color = "";

  try {
    await InsightBot.api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value.trim(),
        password: form.password.value,
      }),
    });
    msg.textContent = "Registered. An admin must approve your account before you can log in.";
    msg.className = "font-body-md text-body-md mt-4 font-medium";
    msg.style.color = "#006b5f";
    form.reset();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "font-body-md text-body-md mt-4 font-medium";
    msg.style.color = "#991B1B";
  }
});

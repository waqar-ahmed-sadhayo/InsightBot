document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("register-message");
  msg.textContent = "";
  msg.className = "font-body-md text-body-md mt-4";

  try {
    await InsightBot.api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value.trim(),
        password: form.password.value,
      }),
    });
    msg.textContent = "Registered. An admin must approve your account before you can log in.";
    msg.className = "font-body-md text-body-md mt-4 font-medium text-emerald-600 dark:text-emerald-400";
    form.reset();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "font-body-md text-body-md mt-4 font-medium text-red-600 dark:text-rose-300";
  }
});

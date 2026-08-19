(async function () {
  const gate = document.getElementById("admin-gate");
  const list = document.getElementById("pending-list");

  if (!InsightBot.isLoggedIn()) {
    gate.innerHTML = `Please <a href="/login">log in</a> as an admin to view this page.`;
    return;
  }
  const user = InsightBot.getUser();
  if (!user || !user.is_admin) {
    gate.innerHTML = `You need admin privileges to view this page.`;
    gate.className = "message error";
    return;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function renderRow(u) {
    const li = document.createElement("li");
    li.className = "pending-row";
    li.innerHTML = `
      <div class="pending-info">
        <span class="pending-email">${escapeHtml(u.email)}</span>
        <span class="article-meta"><span>requested ${escapeHtml((u.created_at || "").slice(0, 10))}</span></span>
      </div>
      <div class="row-actions">
        <button type="button" class="reject-btn btn-danger-ghost" data-id="${u.id}">Reject</button>
        <button type="button" class="approve-btn" data-id="${u.id}">Approve</button>
      </div>
    `;
    li.querySelector(".approve-btn").addEventListener("click", async (e) => {
      const btn = e.target;
      btn.disabled = true;
      btn.textContent = "Approving...";
      try {
        await InsightBot.api(`/api/auth/approve/${u.id}`, { method: "POST" });
        li.style.opacity = "0";
        setTimeout(() => { li.remove(); maybeShowEmpty(); }, 150);
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Approve";
        InsightBot.toast(err.message, "error");
      }
    });
    li.querySelector(".reject-btn").addEventListener("click", async (e) => {
      const btn = e.target;
      const approveBtn = li.querySelector(".approve-btn");
      btn.disabled = true;
      approveBtn.disabled = true;
      btn.textContent = "Rejecting...";
      try {
        await InsightBot.api(`/api/auth/pending/${u.id}`, { method: "DELETE" });
        li.style.opacity = "0";
        setTimeout(() => { li.remove(); maybeShowEmpty(); }, 150);
      } catch (err) {
        btn.disabled = false;
        approveBtn.disabled = false;
        btn.textContent = "Reject";
        InsightBot.toast(err.message, "error");
      }
    });
    return li;
  }

  function maybeShowEmpty() {
    if (!list.children.length) {
      list.innerHTML = `<li class="message">No pending registrations. New sign-ups will show up here.</li>`;
    }
  }

  async function load() {
    list.innerHTML = `<li><div class="skeleton" style="height:60px;border-radius:14px;"></div></li>`;
    try {
      const pending = await InsightBot.api("/api/auth/pending");
      list.innerHTML = "";
      pending.forEach((u) => list.appendChild(renderRow(u)));
      maybeShowEmpty();
    } catch (err) {
      list.innerHTML = `<li class="message error">${escapeHtml(err.message)}</li>`;
    }
  }

  load();
})();

(async function () {
  const gate = document.getElementById("admin-gate");
  const body = document.getElementById("admin-body");
  const statsGrid = document.getElementById("stats-grid");
  const sourcesBody = document.getElementById("sources-body");
  const list = document.getElementById("pending-list");

  function showGate(message) {
    document.getElementById("admin-gate-text").textContent = message;
    gate.classList.remove("hidden");
    gate.classList.add("flex");
    body.remove();
  }

  if (!InsightBot.isLoggedIn()) {
    showGate("Please log in as an admin to view this page.");
    return;
  }
  const user = InsightBot.getUser();
  if (!user || !user.is_admin) {
    showGate("You need admin privileges to view this page.");
    return;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function statCard(icon, label, value) {
    return `
      <div class="bg-surface-container-lowest dark:bg-inverse-surface border border-outline-variant dark:border-outline rounded-xl p-6 flex flex-col">
        <div class="flex justify-between items-start mb-4">
          <span class="font-label-md text-label-md text-on-surface-variant dark:text-outline-variant uppercase tracking-wider">${label}</span>
          <span class="material-symbols-outlined text-primary dark:text-primary-fixed bg-primary-fixed dark:bg-primary-fixed-dim/30 rounded-full p-2" aria-hidden="true">${icon}</span>
        </div>
        <span class="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg font-bold text-on-surface dark:text-surface-bright">${value}</span>
      </div>`;
  }

  async function loadStats() {
    try {
      const stats = await InsightBot.api("/api/dashboard/stats");
      statsGrid.innerHTML = [
        statCard("article", "Total Articles", stats.total_articles),
        statCard("hub", "Active Sources", stats.by_domain.length),
      ].join("");
      sourcesBody.innerHTML = stats.by_domain.length
        ? stats.by_domain.map(([domain, count]) => `
            <tr class="border-b border-outline-variant dark:border-outline last:border-0 hover:bg-surface-container-low dark:hover:bg-on-surface-variant/20 transition-colors">
              <td class="py-3 px-2 font-medium text-on-surface dark:text-surface-bright">${escapeHtml(domain || "(unknown)")}</td>
              <td class="py-3 px-2 text-end text-on-surface-variant dark:text-outline-variant">${count}</td>
            </tr>`).join("")
        : `<tr><td colspan="2" class="py-6 text-center text-on-surface-variant dark:text-outline-variant">No sources yet -- run the ingestion pipeline.</td></tr>`;
    } catch (err) {
      statsGrid.innerHTML = "";
      InsightBot.toast(err.message, "error");
    }
  }

  function renderRow(u) {
    const li = document.createElement("li");
    li.className = "bg-surface-container dark:bg-surface-dim/10 border border-outline-variant dark:border-outline rounded-lg p-4 flex items-center justify-between gap-3 transition-opacity";
    li.innerHTML = `
      <div class="min-w-0">
        <p class="font-label-md text-label-md text-on-surface dark:text-surface-bright truncate">${escapeHtml(u.email)}</p>
        <p class="font-label-sm text-label-sm text-on-surface-variant dark:text-outline-variant mt-0.5">requested ${escapeHtml((u.created_at || "").slice(0, 10))}</p>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <button type="button" class="reject-btn px-3 py-1.5 rounded-lg border border-error/40 text-error dark:text-tertiary-fixed font-label-md text-label-md hover:bg-error-container/20 transition-colors" data-id="${u.id}">Reject</button>
        <button type="button" class="approve-btn px-3 py-1.5 rounded-lg bg-primary text-on-primary font-label-md text-label-md hover:bg-primary-container transition-colors" data-id="${u.id}">Approve</button>
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
      list.innerHTML = `<li class="text-center py-6 font-body-md text-body-md text-on-surface-variant dark:text-outline-variant">No pending registrations. New sign-ups will show up here.</li>`;
    }
  }

  async function loadPending() {
    list.innerHTML = `<li><div class="skeleton h-14 rounded-lg"></div></li>`;
    try {
      const pending = await InsightBot.api("/api/auth/pending");
      list.innerHTML = "";
      pending.forEach((u) => list.appendChild(renderRow(u)));
      maybeShowEmpty();
    } catch (err) {
      list.innerHTML = `<li class="text-center py-6 font-body-md text-body-md" style="color:#991B1B;">${escapeHtml(err.message)}</li>`;
    }
  }

  loadStats();
  loadPending();
})();

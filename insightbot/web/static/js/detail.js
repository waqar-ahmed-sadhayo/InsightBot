(async function () {
  const container = document.getElementById("article-detail");
  const articleId = container.dataset.articleId;

  if (!InsightBot.isLoggedIn()) {
    container.innerHTML = `<p>Please <a href="/login">log in</a> to view this article.</p>`;
    return;
  }

  container.innerHTML = `
    <div class="skeleton" style="height:20px;width:70px;border-radius:999px;margin-bottom:12px;"></div>
    <div class="skeleton" style="height:32px;width:85%;border-radius:8px;margin-bottom:10px;"></div>
    <div class="skeleton" style="height:16px;width:40%;border-radius:6px;margin-bottom:24px;"></div>
    <div class="skeleton" style="height:14px;width:100%;border-radius:6px;margin-bottom:8px;"></div>
    <div class="skeleton" style="height:14px;width:96%;border-radius:6px;margin-bottom:8px;"></div>
    <div class="skeleton" style="height:14px;width:88%;border-radius:6px;"></div>
  `;

  function starIcon() {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.2 1 6-5.2-2.8-5.2 2.8 1-6-4.3-4.2 5.9-.8L12 3.5z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  }

  try {
    const a = await InsightBot.api(`/api/articles/${articleId}`);
    let saved = false;
    try {
      const ids = await InsightBot.api("/api/bookmarks/ids");
      saved = ids.includes(a.id);
    } catch (err) { /* non-fatal */ }

    container.innerHTML = `
      <span class="badge" data-lang="${escapeHtml(a.language || "")}">${escapeHtml(a.language || "")}</span>
      <h1>${escapeHtml(a.title || "(untitled)")}</h1>
      <div class="article-meta">
        <span>${escapeHtml(a.domain || "")}</span>
        <span>${escapeHtml(a.date || "date unknown")}</span>
        <a href="${a.source_url}" target="_blank" rel="noopener">Original source &rarr;</a>
        <button type="button" id="detail-star-btn" class="star-btn detail-star-btn${saved ? " saved" : ""}" title="Save article" aria-label="Save article">${starIcon()}</button>
      </div>
      <div class="body-text">${escapeHtml(a.body || "(no body extracted)")}</div>
    `;

    document.getElementById("detail-star-btn").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      const nowSaved = btn.classList.contains("saved");
      btn.disabled = true;
      try {
        if (nowSaved) {
          await InsightBot.api(`/api/bookmarks/${encodeURIComponent(a.id)}`, { method: "DELETE" });
          btn.classList.remove("saved");
          InsightBot.toast("Removed from saved articles", "success");
        } else {
          await InsightBot.api("/api/bookmarks", { method: "POST", body: JSON.stringify({ article_id: a.id }) });
          btn.classList.add("saved", "pop");
          setTimeout(() => btn.classList.remove("pop"), 400);
          InsightBot.toast("Saved article", "success");
        }
      } catch (err) {
        InsightBot.toast(err.message, "error");
      } finally {
        btn.disabled = false;
      }
    });
  } catch (err) {
    container.innerHTML = `<p class="message error">${escapeHtml(err.message)}</p>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
})();

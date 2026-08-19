(async function () {
  const gate = document.getElementById("gate-message");
  const list = document.getElementById("article-list");
  const statsRow = document.getElementById("stats-row");
  const pageIndicator = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const domainFilter = document.getElementById("domain-filter");
  const savedToggle = document.getElementById("saved-toggle");

  if (!InsightBot.isLoggedIn()) {
    gate.innerHTML = `Please <a href="/login">log in</a> to view articles.`;
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const language = params.get("language") || "";
  const domain = params.get("domain") || "";
  const query = params.get("q") || "";
  const savedOnly = params.get("saved") === "true";
  let page = parseInt(params.get("page") || "1", 10);
  const perPage = 20;

  let bookmarkIds = new Set();

  function navigateWith(changes) {
    const p = new URLSearchParams(window.location.search);
    Object.entries(changes).forEach(([k, v]) => {
      if (v) p.set(k, v); else p.delete(k);
    });
    p.delete("page");
    window.location.href = `/?${p.toString()}`;
  }

  savedToggle.classList.toggle("active", savedOnly);
  savedToggle.addEventListener("click", () => navigateWith({ saved: savedOnly ? "" : "true" }));

  domainFilter.disabled = savedOnly;
  domainFilter.addEventListener("change", () => navigateWith({ domain: domainFilter.value }));

  async function loadDomains() {
    try {
      const domains = await InsightBot.api("/api/articles/domains");
      domainFilter.innerHTML = `<option value="">All domains</option>` +
        domains.map((d) => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join("");
      domainFilter.value = domain;
    } catch (err) { /* non-fatal */ }
  }

  const LANG_NAMES = { en: "English", ar: "Arabic", ru: "Russian" };

  async function loadStats() {
    try {
      const stats = await InsightBot.api("/api/dashboard/stats");
      statsRow.innerHTML = [
        `<div class="stat-card"><span class="stat-value">${stats.total_articles}</span><span class="stat-label">Total articles</span></div>`,
        ...stats.by_language.map(([lang, count]) => `
          <div class="stat-card" data-lang="${escapeHtml(lang)}">
            <span class="stat-value">${count}</span>
            <span class="stat-label">${escapeHtml(LANG_NAMES[lang] || lang || "Unknown")}</span>
          </div>`),
      ].join("");
    } catch (err) {
      statsRow.textContent = "";
    }
  }

  async function loadBookmarkIds() {
    try {
      bookmarkIds = new Set(await InsightBot.api("/api/bookmarks/ids"));
    } catch (err) {
      bookmarkIds = new Set();
    }
  }

  function skeletonCard() {
    return `<li><div class="skeleton" style="height:84px;border-radius:14px;"></div></li>`;
  }

  function matchesFilters(a) {
    if (language && a.language !== language) return false;
    if (domain && a.domain !== domain) return false;
    if (query) {
      const hay = `${a.title || ""} ${a.body || ""}`.toLowerCase();
      if (!hay.includes(query.toLowerCase())) return false;
    }
    return true;
  }

  async function fetchArticles() {
    if (savedOnly) {
      const data = await InsightBot.api("/api/bookmarks?per_page=200");
      const filtered = data.items.filter(matchesFilters);
      const start = Math.max(page - 1, 0) * perPage;
      return { total: filtered.length, items: filtered.slice(start, start + perPage) };
    }
    const path = query
      ? `/api/articles/search?q=${encodeURIComponent(query)}&language=${language}&domain=${encodeURIComponent(domain)}&page=${page}&per_page=${perPage}`
      : `/api/articles?language=${language}&domain=${encodeURIComponent(domain)}&page=${page}&per_page=${perPage}`;
    return InsightBot.api(path);
  }

  async function toggleBookmark(articleId, btn) {
    const saved = bookmarkIds.has(articleId);
    btn.disabled = true;
    try {
      if (saved) {
        await InsightBot.api(`/api/bookmarks/${encodeURIComponent(articleId)}`, { method: "DELETE" });
        bookmarkIds.delete(articleId);
        btn.classList.remove("saved");
      } else {
        await InsightBot.api("/api/bookmarks", { method: "POST", body: JSON.stringify({ article_id: articleId }) });
        bookmarkIds.add(articleId);
        btn.classList.add("saved", "pop");
        setTimeout(() => btn.classList.remove("pop"), 400);
      }
      if (savedOnly && saved) {
        btn.closest("li").remove();
        if (!list.children.length) list.innerHTML = `<li class="message">No saved articles yet.</li>`;
      }
    } catch (err) {
      InsightBot.toast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  }

  function starIcon() {
    return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.2 1 6-5.2-2.8-5.2 2.8 1-6-4.3-4.2 5.9-.8L12 3.5z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  }

  async function loadArticles() {
    list.innerHTML = skeletonCard() + skeletonCard() + skeletonCard();
    try {
      const data = await fetchArticles();

      if (!data.items.length) {
        list.innerHTML = `<li class="message">${savedOnly ? "No saved articles yet." : "No articles found."}</li>`;
      } else {
        list.innerHTML = data.items.map((a) => `
          <li>
            <a class="article-card" href="/articles/${a.id}">
              <button type="button" class="star-btn${bookmarkIds.has(a.id) ? " saved" : ""}" data-id="${escapeHtml(a.id)}" title="Save article" aria-label="Save article">${starIcon()}</button>
              <h3>${escapeHtml(a.title || "(untitled)")}</h3>
              <div class="article-meta">
                <span class="badge" data-lang="${escapeHtml(a.language || "")}">${escapeHtml(a.language || "")}</span>
                <span>${escapeHtml(a.domain || "")}</span>
                <span>${escapeHtml(a.date || "date unknown")}</span>
              </div>
            </a>
          </li>`).join("");

        list.querySelectorAll(".star-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleBookmark(btn.dataset.id, btn);
          });
        });
      }

      const totalPages = Math.max(Math.ceil(data.total / perPage), 1);
      pageIndicator.textContent = `Page ${page} of ${totalPages}`;
      prevBtn.disabled = page <= 1;
      nextBtn.disabled = page >= totalPages;
    } catch (err) {
      list.innerHTML = `<li class="message error">${escapeHtml(err.message)}</li>`;
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function updatePageParam(newPage) {
    const p = new URLSearchParams(window.location.search);
    p.set("page", newPage);
    window.history.replaceState({}, "", `/?${p.toString()}`);
    page = newPage;
    loadArticles();
  }

  prevBtn.addEventListener("click", () => { if (page > 1) updatePageParam(page - 1); });
  nextBtn.addEventListener("click", () => updatePageParam(page + 1));

  loadStats();
  loadDomains();
  await loadBookmarkIds();
  loadArticles();
})();

(async function () {
  const gate = document.getElementById("gate-message");
  const listError = document.getElementById("list-error");
  const list = document.getElementById("article-list");
  const statsRow = document.getElementById("stats-row");
  const pageIndicator = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const domainFilter = document.getElementById("domain-filter");
  const savedToggle = document.getElementById("saved-toggle");
  const pageHeading = document.getElementById("page-heading");
  const pager = document.getElementById("pager");

  function showBanner(el, message) {
    document.getElementById(`${el.id}-text`).textContent = message;
    el.classList.remove("hidden");
    el.classList.add("flex");
  }
  function hideBanner(el) {
    el.classList.add("hidden");
    el.classList.remove("flex");
  }

  if (!InsightBot.isLoggedIn()) {
    document.getElementById("gate-message-text").innerHTML = `Please <a href="/login" class="underline font-medium">log in</a> to view articles.`;
    gate.classList.remove("hidden");
    gate.classList.add("flex");
    document.getElementById("stats-row").remove();
    document.querySelector("section.mb-6").remove();
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

  if (savedOnly) pageHeading.textContent = "Saved articles";

  function navigateWith(changes) {
    const p = new URLSearchParams(window.location.search);
    Object.entries(changes).forEach(([k, v]) => {
      if (v) p.set(k, v); else p.delete(k);
    });
    p.delete("page");
    window.location.href = `/?${p.toString()}`;
  }

  document.addEventListener("insightbot:search", (e) => navigateWith({ q: e.detail.q }));

  const PILL_ACTIVE = "bg-primary-container dark:bg-primary-fixed-dim text-on-primary-container dark:text-on-primary-fixed";
  const PILL_INACTIVE = "bg-surface-container-lowest dark:bg-inverse-surface border border-outline-variant dark:border-outline text-on-surface-variant dark:text-outline-variant hover:bg-surface-container-low dark:hover:bg-on-surface-variant/30";
  document.querySelectorAll(".lang-pill").forEach((pill) => {
    const active = pill.dataset.lang === language;
    pill.className = `lang-pill px-4 py-1.5 rounded-full font-label-md text-label-md transition-colors ${active ? PILL_ACTIVE : PILL_INACTIVE}`;
    pill.addEventListener("click", () => navigateWith({ language: pill.dataset.lang }));
  });

  const SAVED_ACTIVE = "flex items-center gap-1.5 px-4 py-2 rounded-full font-label-md text-label-md whitespace-nowrap transition-colors bg-primary text-on-primary";
  const SAVED_INACTIVE = "flex items-center gap-1.5 px-4 py-2 rounded-full border border-outline-variant dark:border-outline text-on-surface-variant dark:text-outline-variant font-label-md text-label-md whitespace-nowrap transition-colors hover:bg-surface-container-high dark:hover:bg-on-surface-variant/30";
  savedToggle.className = savedOnly ? SAVED_ACTIVE : SAVED_INACTIVE;
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
      const cardCls = "bg-surface-container-lowest dark:bg-inverse-surface border border-outline-variant dark:border-outline rounded-lg p-3 flex flex-col";
      statsRow.innerHTML = [
        `<div class="${cardCls}"><span class="font-headline-md text-headline-md font-bold text-on-surface dark:text-surface-bright">${stats.total_articles}</span><span class="font-label-sm text-label-sm text-on-surface-variant dark:text-outline-variant">Total articles</span></div>`,
        ...stats.by_language.map(([lang, count]) => `
          <div class="${cardCls}">
            <span class="font-headline-md text-headline-md font-bold text-on-surface dark:text-surface-bright">${count}</span>
            <span class="font-label-sm text-label-sm text-on-surface-variant dark:text-outline-variant">${escapeHtml(LANG_NAMES[lang] || lang || "Unknown")}</span>
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
    return `<div class="bg-surface-container-lowest dark:bg-inverse-surface border border-outline-variant dark:border-outline rounded-xl p-5">
      <div class="skeleton h-5 w-3/4 rounded mb-3"></div>
      <div class="skeleton h-4 w-full rounded mb-2"></div>
      <div class="skeleton h-4 w-5/6 rounded"></div>
    </div>`;
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
        setBookmarkIcon(btn, false);
      } else {
        await InsightBot.api("/api/bookmarks", { method: "POST", body: JSON.stringify({ article_id: articleId }) });
        bookmarkIds.add(articleId);
        setBookmarkIcon(btn, true);
      }
      if (savedOnly && saved) {
        btn.closest("article").remove();
        if (!list.children.length) renderEmptyState();
      }
    } catch (err) {
      InsightBot.toast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  }

  function setBookmarkIcon(btn, saved) {
    btn.innerHTML = `<span class="material-symbols-outlined" ${saved ? "style=\"font-variation-settings: 'FILL' 1;\"" : ""} aria-hidden="true">bookmark</span>`;
    btn.className = saved
      ? "text-primary dark:text-primary-fixed-dim hover:bg-primary-container/20 dark:hover:bg-on-surface-variant/30 rounded-full p-1.5 transition-colors flex-shrink-0"
      : "text-outline dark:text-outline-variant hover:text-on-surface dark:hover:text-surface-bright hover:bg-surface-container-high dark:hover:bg-on-surface-variant/30 rounded-full p-1.5 transition-colors flex-shrink-0";
  }

  function langBadge(lang) {
    if (lang === "ar") return `<span class="ms-auto bg-tertiary-container/10 text-tertiary dark:text-tertiary-fixed px-2 py-0.5 rounded font-label-sm text-label-sm border border-tertiary/20">Arabic</span>`;
    const names = { en: "EN", ru: "RU" };
    return `<span class="ms-auto bg-surface-container dark:bg-on-surface-variant/30 text-on-surface-variant dark:text-outline-variant px-2 py-0.5 rounded font-label-sm text-label-sm border border-outline-variant/30 dark:border-outline/30">${escapeHtml(names[lang] || lang || "?")}</span>`;
  }

  function renderCard(a) {
    const isRtl = a.language === "ar";
    const saved = bookmarkIds.has(a.id);
    return `
      <article dir="${isRtl ? "rtl" : "ltr"}" class="bg-surface-container-lowest dark:bg-inverse-surface border border-outline-variant dark:border-outline rounded-xl p-5 hover:shadow-md transition-shadow flex flex-col gap-3 group relative">
        <div class="flex justify-between items-start gap-4">
          <a href="/articles/${a.id}" class="font-headline-md text-headline-md text-on-surface dark:text-surface-bright hover:text-primary dark:hover:text-primary-fixed-dim transition-colors ${isRtl ? "font-sans" : ""}">${escapeHtml(a.title || "(untitled)")}</a>
          <button type="button" class="star-btn flex-shrink-0" data-id="${escapeHtml(a.id)}" title="Save article" aria-label="Save article"></button>
        </div>
        <a href="/articles/${a.id}" class="font-body-md text-body-md text-on-surface-variant dark:text-outline-variant line-clamp-2">${escapeHtml((a.body || "").slice(0, 220))}</a>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 mt-2 pt-3 border-t border-outline-variant/40 dark:border-outline/30">
          <div class="flex items-center gap-1.5 text-on-surface-variant dark:text-outline-variant">
            <span class="material-symbols-outlined text-[16px]" aria-hidden="true">public</span>
            <span class="font-label-sm text-label-sm">${escapeHtml(a.domain || "")}</span>
          </div>
          <div class="flex items-center gap-1.5 text-on-surface-variant dark:text-outline-variant">
            <span class="material-symbols-outlined text-[16px]" aria-hidden="true">calendar_today</span>
            <span class="font-label-sm text-label-sm">${escapeHtml(a.date || "date unknown")}</span>
          </div>
          ${langBadge(a.language)}
        </div>
      </article>`;
  }

  function renderEmptyState() {
    list.innerHTML = `
      <div class="col-span-full flex flex-col items-center justify-center text-center py-16 px-4">
        <div class="w-28 h-28 mb-6 rounded-full bg-surface-container dark:bg-inverse-surface flex items-center justify-center">
          <span class="material-symbols-outlined text-5xl text-outline-variant dark:text-outline" aria-hidden="true">${savedOnly ? "bookmark" : "search_off"}</span>
        </div>
        <h2 class="font-headline-md text-headline-md text-on-surface dark:text-surface-bright mb-2">${savedOnly ? "No saved articles yet" : "No articles found"}</h2>
        <p class="font-body-md text-body-md text-on-surface-variant dark:text-outline-variant mb-8 max-w-[320px]">${savedOnly ? "Bookmark articles to see them here and read them later." : "Try a different language, domain, or search term."}</p>
        ${savedOnly ? `<a href="/" class="bg-primary text-on-primary font-label-md text-label-md px-6 py-3 rounded-xl shadow-sm hover:shadow-md transition-shadow">Browse Articles</a>` : ""}
      </div>`;
    pager.classList.add("hidden");
  }

  async function loadArticles() {
    list.innerHTML = skeletonCard() + skeletonCard() + skeletonCard();
    pager.classList.remove("hidden");
    try {
      const data = await fetchArticles();
      hideBanner(listError);

      if (!data.items.length) {
        renderEmptyState();
      } else {
        list.innerHTML = data.items.map(renderCard).join("");
        list.querySelectorAll(".star-btn").forEach((btn) => {
          setBookmarkIcon(btn, bookmarkIds.has(btn.dataset.id));
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
      list.innerHTML = "";
      showBanner(listError, err.message);
      pager.classList.add("hidden");
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

(async function () {
  const container = document.getElementById("article-detail");
  const errorBanner = document.getElementById("detail-error");
  const articleId = container.dataset.articleId;

  function showBanner(el, message) {
    document.getElementById(`${el.id}-text`).textContent = message;
    el.classList.remove("hidden");
    el.classList.add("flex");
  }

  if (!InsightBot.isLoggedIn()) {
    container.innerHTML = `<p class="font-body-md text-body-md">Please <a href="/login" class="text-primary dark:text-primary-fixed-dim underline">log in</a> to view this article.</p>`;
    return;
  }

  const LANG_NAMES = { en: "English", ar: "Arabic", ru: "Russian" };

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function readTime(body) {
    const words = (body || "").trim().split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
  }

  async function shareArticle(a) {
    const shareData = { title: a.title || "InsightBot article", url: window.location.href };
    if (navigator.share) {
      try { await navigator.share(shareData); } catch (err) { /* user cancelled */ }
    } else {
      copyLink();
    }
  }

  function copyLink() {
    navigator.clipboard.writeText(window.location.href).then(
      () => InsightBot.toast("Link copied to clipboard", "success"),
      () => InsightBot.toast("Could not copy link", "error")
    );
  }

  try {
    const a = await InsightBot.api(`/api/articles/${articleId}`);
    let saved = false;
    try {
      const ids = await InsightBot.api("/api/bookmarks/ids");
      saved = ids.includes(a.id);
    } catch (err) { /* non-fatal */ }

    const isRtl = a.language === "ar";
    container.setAttribute("dir", isRtl ? "rtl" : "ltr");

    container.innerHTML = `
      <div class="flex items-center gap-3 mb-4 flex-wrap">
        <span class="bg-surface-container-high dark:bg-[#334155] text-primary dark:text-primary-fixed-dim px-3 py-1 rounded-full font-label-md text-label-md flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]" aria-hidden="true">language</span>
          ${escapeHtml(LANG_NAMES[a.language] || a.language || "Unknown")}
        </span>
        <span class="text-on-surface-variant dark:text-[#94a3b8] font-label-sm text-label-sm flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]" aria-hidden="true">calendar_today</span>
          ${escapeHtml(a.date || "date unknown")}
        </span>
        <span class="text-on-surface-variant dark:text-[#94a3b8] font-label-sm text-label-sm flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]" aria-hidden="true">schedule</span>
          ${readTime(a.body)} min read
        </span>
      </div>
      <h1 class="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-on-surface dark:text-[#f8fafc] mb-4">${escapeHtml(a.title || "(untitled)")}</h1>
      <div class="flex items-center justify-between gap-4 mb-6 pb-6 border-b border-outline-variant dark:border-[#334155]">
        <p class="font-label-sm text-label-sm text-on-surface-variant dark:text-[#94a3b8] flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]" aria-hidden="true">domain</span>
          via ${escapeHtml(a.domain || "unknown source")}
          <a href="${a.source_url}" target="_blank" rel="noopener" class="ms-2 text-primary dark:text-primary-fixed-dim hover:underline inline-flex items-center gap-0.5">
            Original <span class="material-symbols-outlined icon-mirror text-[14px]" aria-hidden="true">arrow_forward</span>
          </a>
        </p>
        <button type="button" id="detail-star-btn" class="rounded-full p-1.5 transition-colors flex-shrink-0" title="Save article" aria-label="Save article"></button>
      </div>
      ${a.image ? `<img src="${escapeHtml(a.image)}" alt="" loading="lazy" class="w-full max-h-[360px] object-cover rounded-xl border border-outline-variant dark:border-[#334155] mb-6" onerror="this.remove()">` : ""}
      <div class="article-body font-body-lg text-body-lg text-on-background dark:text-[#f8fafc] ${isRtl ? "font-sans" : ""}">${escapeHtml(a.body || "(no body extracted)")}</div>
      <section class="flex flex-col items-center gap-4 py-8 mt-4 border-t border-outline-variant dark:border-[#334155]">
        <h3 class="font-label-md text-label-md text-on-surface-variant dark:text-[#94a3b8] uppercase tracking-wider">Share this article</h3>
        <div class="flex gap-4">
          <button type="button" id="share-btn" class="w-12 h-12 rounded-full bg-surface-container-highest dark:bg-[#1e293b] hover:bg-surface-variant dark:hover:bg-[#334155] text-primary dark:text-primary-fixed-dim flex items-center justify-center shadow-sm transition-colors" title="Share">
            <span class="material-symbols-outlined" aria-hidden="true">share</span>
          </button>
          <button type="button" id="copy-link-btn" class="w-12 h-12 rounded-full bg-surface-container-highest dark:bg-[#1e293b] hover:bg-surface-variant dark:hover:bg-[#334155] text-primary dark:text-primary-fixed-dim flex items-center justify-center shadow-sm transition-colors" title="Copy link">
            <span class="material-symbols-outlined" aria-hidden="true">link</span>
          </button>
          <a href="mailto:?subject=${encodeURIComponent(a.title || "InsightBot article")}&body=${encodeURIComponent(window.location.href)}" class="w-12 h-12 rounded-full bg-surface-container-highest dark:bg-[#1e293b] hover:bg-surface-variant dark:hover:bg-[#334155] text-primary dark:text-primary-fixed-dim flex items-center justify-center shadow-sm transition-colors" title="Email">
            <span class="material-symbols-outlined" aria-hidden="true">mail</span>
          </a>
        </div>
        <button type="button" disabled title="Coming soon"
          class="gradient-accent text-white font-label-md text-label-md mt-2 px-6 py-3 rounded-full shadow-md flex items-center gap-2 opacity-60 cursor-not-allowed">
          <span class="material-symbols-outlined text-[18px]" aria-hidden="true">summarize</span>
          Generate AI Summary
          <span class="text-[10px] font-normal opacity-80">(Coming soon)</span>
        </button>
      </section>
    `;

    const starBtn = document.getElementById("detail-star-btn");
    function setStar(isSaved) {
      starBtn.innerHTML = `<span class="material-symbols-outlined" ${isSaved ? "style=\"font-variation-settings: 'FILL' 1;\"" : ""} aria-hidden="true">bookmark</span>`;
      starBtn.className = isSaved
        ? "rounded-full p-1.5 transition-colors flex-shrink-0 text-primary dark:text-primary-fixed-dim hover:bg-primary-container/20 dark:hover:bg-[#334155]"
        : "rounded-full p-1.5 transition-colors flex-shrink-0 text-outline dark:text-[#94a3b8] hover:text-on-surface dark:hover:text-surface-bright hover:bg-surface-container-high dark:hover:bg-[#334155]";
    }
    setStar(saved);

    starBtn.addEventListener("click", async () => {
      const nowSaved = saved;
      starBtn.disabled = true;
      try {
        if (nowSaved) {
          await InsightBot.api(`/api/bookmarks/${encodeURIComponent(a.id)}`, { method: "DELETE" });
          saved = false;
          InsightBot.toast("Removed from saved articles", "success");
        } else {
          await InsightBot.api("/api/bookmarks", { method: "POST", body: JSON.stringify({ article_id: a.id }) });
          saved = true;
          InsightBot.toast("Saved article", "success");
        }
        setStar(saved);
      } catch (err) {
        InsightBot.toast(err.message, "error");
      } finally {
        starBtn.disabled = false;
      }
    });

    document.getElementById("share-btn").addEventListener("click", () => shareArticle(a));
    document.getElementById("copy-link-btn").addEventListener("click", copyLink);
  } catch (err) {
    container.innerHTML = "";
    showBanner(errorBanner, err.message);
    container.remove();
  }
})();

// Shared helpers: auth token storage, API fetch wrapper, and the shell
// controls (sidebar, top bar, theme/RTL toggles) present on every page.
const InsightBot = (() => {
  const TOKEN_KEY = "insightbot_token";
  const USER_KEY = "insightbot_user";
  const THEME_KEY = "insightbot_theme";
  const UI_LANG_KEY = "insightbot_ui_lang";

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function isLoggedIn() { return !!getToken(); }

  async function api(path, options = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const resp = await fetch(path, Object.assign({}, options, { headers }));
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const err = new Error(data.error || `Request failed (${resp.status})`);
      err.status = resp.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function renderAuthArea() {
    const el = document.getElementById("auth-area");
    const sidebarUser = document.getElementById("sidebar-user");
    const user = getUser();
    if (user) {
      const initial = (user.email || "?").trim().charAt(0).toUpperCase();
      if (el) {
        el.innerHTML = `
          <button id="logout-btn" class="hidden sm:flex items-center gap-2 text-on-surface-variant dark:text-outline-variant hover:bg-surface-container-high dark:hover:bg-on-surface-variant/40 rounded-full ps-1 pe-3 py-1 transition-colors" title="Log out">
            <span class="w-7 h-7 rounded-full bg-primary text-on-primary flex items-center justify-center font-label-md text-label-md">${initial}</span>
            <span class="font-label-md text-label-md truncate max-w-[120px]">${user.email}</span>
          </button>`;
        document.getElementById("logout-btn").addEventListener("click", () => {
          clearSession();
          window.location.href = "/login";
        });
      }
      if (sidebarUser) {
        sidebarUser.innerHTML = `
          <span class="w-9 h-9 rounded-full bg-primary text-on-primary flex items-center justify-center font-label-md text-label-md shrink-0">${initial}</span>
          <div class="flex flex-col min-w-0 flex-1">
            <span class="font-label-md text-label-md text-on-surface dark:text-surface-bright truncate">${user.email}</span>
            <span class="font-label-sm text-label-sm text-on-surface-variant dark:text-outline-variant">${user.is_admin ? "Admin" : "Member"}</span>
          </div>
          <button id="logout-btn-sidebar" class="material-symbols-outlined text-on-surface-variant dark:text-outline-variant hover:text-error text-[20px]" title="Log out">logout</button>`;
        document.getElementById("logout-btn-sidebar").addEventListener("click", () => {
          clearSession();
          window.location.href = "/login";
        });
      }
    } else if (el) {
      el.innerHTML = `<a href="/login" class="font-label-md text-label-md text-primary dark:text-primary-fixed-dim px-3 py-2">Log in</a>`;
    }
  }

  function wireSidebar() {
    const user = getUser();
    const loggedIn = !!user;

    document.querySelectorAll("[data-auth-only]").forEach((el) => { el.style.display = loggedIn ? "" : "none"; });
    document.querySelectorAll("[data-admin-only]").forEach((el) => { el.style.display = (loggedIn && user.is_admin) ? "" : "none"; });
    document.querySelectorAll("[data-guest-only]").forEach((el) => { el.style.display = loggedIn ? "none" : ""; });

    const current = window.location.pathname + (window.location.search.includes("saved=true") ? "?saved=true" : "");
    document.querySelectorAll(".sidebar-link").forEach((link) => {
      link.classList.toggle("active", link.dataset.path === current);
    });

    const toggleBtn = document.getElementById("sidebar-toggle");
    const drawer = document.getElementById("sidebar-mobile");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (toggleBtn && drawer && backdrop) {
      const open = () => { drawer.classList.add("open"); backdrop.classList.remove("hidden"); backdrop.classList.add("open"); };
      const close = () => { drawer.classList.remove("open"); backdrop.classList.add("hidden"); backdrop.classList.remove("open"); };
      toggleBtn.addEventListener("click", open);
      backdrop.addEventListener("click", close);
      drawer.querySelectorAll("a").forEach((a) => a.addEventListener("click", close));
    }
  }

  function toast(message, type = "success", timeout = 3500) {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => el.remove(), timeout);
  }

  const LANG_LABELS = { "": "Default", en: "English", ar: "العربية", ru: "Русский" };

  function applyUiDirection(lang) {
    const rtl = lang === "ar";
    document.documentElement.setAttribute("dir", rtl ? "rtl" : "ltr");
    document.documentElement.setAttribute("lang", lang || "en");
    localStorage.setItem("insightbot_dir", rtl ? "rtl" : "ltr");
  }

  // Top-bar globe menu: a UI-wide direction/locale preference (RTL preview),
  // independent of the per-page article-language content filter.
  function wireLangMenu() {
    const btn = document.getElementById("lang-menu-btn");
    const menu = document.getElementById("lang-menu");
    const label = document.getElementById("lang-menu-label");
    if (!btn || !menu) return;

    const initialLang = localStorage.getItem(UI_LANG_KEY) || "";
    if (label) label.textContent = LANG_LABELS[initialLang] || "All";
    applyUiDirection(initialLang);

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("hidden");
    });
    document.addEventListener("click", () => menu.classList.add("hidden"));

    menu.querySelectorAll(".lang-option").forEach((opt) => {
      opt.addEventListener("click", () => {
        const lang = opt.dataset.lang;
        localStorage.setItem(UI_LANG_KEY, lang);
        if (label) label.textContent = LANG_LABELS[lang] || "All";
        applyUiDirection(lang);
        menu.classList.add("hidden");
      });
    });
  }

  function wireSearchBox() {
    const searchBox = document.getElementById("search-box");
    if (!searchBox) return;
    const params = new URLSearchParams(window.location.search);
    searchBox.value = params.get("q") || "";
    searchBox.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      document.dispatchEvent(new CustomEvent("insightbot:search", { detail: { q: searchBox.value.trim() } }));
    });
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchBox.focus();
      }
    });
  }

  function wireThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    function currentTheme() {
      return localStorage.getItem(THEME_KEY) || (prefersDark ? "dark" : "light");
    }
    function apply(theme) {
      document.documentElement.classList.toggle("dark", theme === "dark");
    }

    apply(currentTheme());

    btn.addEventListener("click", () => {
      const next = currentTheme() === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      apply(next);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderAuthArea();
    wireSidebar();
    wireLangMenu();
    wireSearchBox();
    wireThemeToggle();
  });

  return { getToken, getUser, setSession, clearSession, isLoggedIn, api, toast };
})();

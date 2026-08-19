// Shared helpers: auth token storage, API fetch wrapper, and the
// header controls (language toggle + search box) present on every page.
const InsightBot = (() => {
  const TOKEN_KEY = "insightbot_token";
  const USER_KEY = "insightbot_user";

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
    if (!el) return;
    const user = getUser();
    if (user) {
      const initial = (user.email || "?").trim().charAt(0).toUpperCase();
      el.innerHTML = `
        <span class="user-chip">
          <span class="user-avatar">${initial}</span>
          <span class="user-email">${user.email}</span>
        </span>
        <button id="logout-btn" class="btn-ghost">Log out</button>`;
      document.getElementById("logout-btn").addEventListener("click", () => {
        clearSession();
        window.location.href = "/login";
      });
    } else {
      el.innerHTML = `<a href="/login">Log in</a>`;
    }
  }

  function wireSidebar() {
    const sidebar = document.getElementById("sidebar");
    if (!sidebar) return;
    const user = getUser();
    const loggedIn = !!user;

    sidebar.querySelectorAll("[data-auth-only]").forEach((el) => { el.style.display = loggedIn ? "" : "none"; });
    sidebar.querySelectorAll("[data-admin-only]").forEach((el) => { el.style.display = (loggedIn && user.is_admin) ? "" : "none"; });
    sidebar.querySelectorAll("[data-guest-only]").forEach((el) => { el.style.display = loggedIn ? "none" : ""; });

    const current = window.location.pathname + (window.location.search.includes("saved=true") ? "?saved=true" : "");
    sidebar.querySelectorAll(".sidebar-link").forEach((link) => {
      link.classList.toggle("active", link.dataset.path === current);
    });

    const toggleBtn = document.getElementById("sidebar-toggle");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (toggleBtn && backdrop) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        backdrop.classList.toggle("open");
      });
      backdrop.addEventListener("click", () => {
        sidebar.classList.remove("open");
        backdrop.classList.remove("open");
      });
    }
  }

  function toast(message, type = "success", timeout = 3500) {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.style.setProperty("--toast-duration", `${timeout}ms`);
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => el.remove(), timeout);
  }

  function wireHeaderControls() {
    const params = new URLSearchParams(window.location.search);
    const langSelect = document.getElementById("lang-toggle");
    const searchBox = document.getElementById("search-box");

    if (langSelect) {
      langSelect.value = params.get("language") || "";
      langSelect.addEventListener("change", () => {
        const p = new URLSearchParams(window.location.search);
        if (langSelect.value) p.set("language", langSelect.value); else p.delete("language");
        p.delete("page");
        window.location.href = `/?${p.toString()}`;
      });
    }
    if (searchBox) {
      searchBox.value = params.get("q") || "";
      searchBox.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        const p = new URLSearchParams(window.location.search);
        if (searchBox.value.trim()) p.set("q", searchBox.value.trim()); else p.delete("q");
        p.delete("page");
        window.location.href = `/?${p.toString()}`;
      });
    }
  }

  function wireThemeToggle() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    const THEME_KEY = "insightbot_theme";
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    function currentTheme() {
      return localStorage.getItem(THEME_KEY) || (prefersDark ? "dark" : "light");
    }
    function apply(theme) {
      document.documentElement.setAttribute("data-theme", theme);
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
    wireHeaderControls();
    wireThemeToggle();
  });

  return { getToken, getUser, setSession, clearSession, isLoggedIn, api, toast };
})();

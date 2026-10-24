(function () {
  "use strict";

  const config = window.SNIPURL_CONFIG || {};
  // Empty API_BASE means the API is served from the same origin as this page.
  const API_BASE = (config.API_BASE || window.location.origin).replace(/\/+$/, "");
  const API_KEY = config.API_KEY || "dev-key";
  const RECENT_KEY = "snipurl.recent";
  const RECENT_LIMIT = 10;

  const $ = (sel) => document.querySelector(sel);

  const form = $("#snip-form");
  const field = $("#snip-field");
  const input = $("#snip-input");
  const submitBtn = $("#snip-submit");
  const submitLabel = $("#snip-submit-label");
  const submitIcon = $("#snip-submit-icon");
  const spinner = $("#snip-spinner");
  const errorEl = $("#snip-error");

  const result = $("#snip-result");
  const resultShort = $("#result-short");
  const resultLong = $("#result-long");
  const resultOpen = $("#result-open");
  const resultCopy = $("#result-copy");
  const resultStats = $("#result-stats");
  const statsPanel = $("#result-stats-panel");

  const recentWrap = $("#recent-wrap");
  const recentList = $("#recent-list");

  let current = null; // { code, longUrl }
  let loading = false;
  let coolingDown = false; // true while waiting out a 429
  let retryTimer = null;

  // ---------- Helpers ----------

  function shortHref(code) {
    return API_BASE + "/" + encodeURIComponent(code);
  }

  function shortDisplay(code) {
    return "snip.url/" + code;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function icon(name, className) {
    const node = document.createElement("iconify-icon");
    node.setAttribute("icon", name);
    if (className) node.className = className;
    return node;
  }

  // Returns a normalized http(s) URL string, or null if the input isn't a usable URL.
  function normalizeUrl(raw) {
    let value = raw.trim();
    if (!value) return null;
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) value = "https://" + value;
    let parsed;
    try {
      parsed = new URL(value);
    } catch (_) {
      return null;
    }
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    // Require something that looks like a real host (a dot or localhost).
    if (!parsed.hostname.includes(".") && parsed.hostname !== "localhost") return null;
    return parsed.href;
  }

  // ---------- Toast ----------

  const toast = $("#toast");
  const toastText = $("#toast-text");
  let toastTimer = null;

  function showToast(message) {
    toastText.textContent = message;
    toast.classList.add("is-shown");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-shown"), 1800);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const ta = el("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    showToast("Copied to clipboard");
  }

  // ---------- API ----------

  class ApiError extends Error {
    constructor(message, retryAfter) {
      super(message);
      this.retryAfter = retryAfter;
    }
  }

  async function api(path, options) {
    let res;
    try {
      res = await fetch(API_BASE + path, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
          ...(options && options.headers),
        },
      });
    } catch (_) {
      throw new ApiError("Can't reach the SnipURL API at " + API_BASE + ". Is the server running?");
    }

    if (res.ok) return res.json();

    if (res.status === 401) {
      throw new ApiError("The API key was rejected. Check API_KEY in ui/config.js.");
    }
    if (res.status === 429) {
      const retryAfter = parseInt(res.headers.get("Retry-After") || "60", 10);
      throw new ApiError("Whoa, slow down — rate limit reached.", retryAfter);
    }
    if (res.status === 404 || res.status >= 500) {
      throw new ApiError(path.startsWith("/stats/") ? "No stats found for that link." : "The server hit an error. Try again.");
    }
    throw new ApiError("Request failed (" + res.status + ").");
  }

  function shortenUrl(longUrl) {
    return api("/shorten", { method: "POST", body: JSON.stringify({ url: longUrl }) });
  }

  function fetchStats(code) {
    return api("/stats/" + encodeURIComponent(code), { method: "GET" });
  }

  // ---------- Form state ----------

  function syncSubmit() {
    submitBtn.disabled = loading || coolingDown;
  }

  function setLoading(isLoading) {
    loading = isLoading;
    syncSubmit();
    spinner.classList.toggle("hidden", !isLoading);
    submitIcon.classList.toggle("hidden", isLoading);
    submitLabel.textContent = isLoading ? "Snipping" : "Snip it";
  }

  function clearError() {
    if (coolingDown) return; // keep the countdown visible until it expires
    errorEl.classList.add("hidden");
    errorEl.textContent = "";
    field.classList.remove("is-invalid");
    input.removeAttribute("aria-invalid");
  }

  function showError(message, retryAfter) {
    errorEl.replaceChildren(icon("lucide:alert-triangle", "shrink-0"), el("span", null, message));
    errorEl.classList.remove("hidden");
    field.classList.add("is-invalid");
    input.setAttribute("aria-invalid", "true");

    if (retryAfter) {
      let remaining = retryAfter;
      const counter = el("span", "text-zinc-500", " Try again in " + remaining + "s.");
      errorEl.appendChild(counter);
      coolingDown = true;
      syncSubmit();
      retryTimer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
          clearInterval(retryTimer);
          coolingDown = false;
          syncSubmit();
          clearError();
          return;
        }
        counter.textContent = " Try again in " + remaining + "s.";
      }, 1000);
    }
  }

  // ---------- Result ----------

  function renderResult(entry) {
    current = entry;
    const href = shortHref(entry.code);
    resultShort.textContent = shortDisplay(entry.code);
    resultShort.href = href;
    resultShort.title = href;
    resultOpen.href = href;
    resultLong.textContent = entry.longUrl;
    resultLong.title = entry.longUrl;
    statsPanel.classList.add("hidden");
    statsPanel.replaceChildren();

    result.classList.remove("hidden");
    // Restart the pop-in animation for repeat snips.
    result.classList.remove("animate-pop");
    void result.offsetWidth;
    result.classList.add("animate-pop");
  }

  function statTile(label, value, extraClass) {
    const tile = el("div", "rounded-xl border border-white/10 bg-black/40 p-4 min-w-0 " + (extraClass || ""));
    tile.appendChild(el("div", "text-[10px] font-bold uppercase tracking-widest text-zinc-500", label));
    tile.appendChild(el("div", "mt-1 text-white font-semibold truncate", value));
    return tile;
  }

  async function showStats(code) {
    statsPanel.classList.remove("hidden");
    statsPanel.replaceChildren(el("div", "sm:col-span-3 text-zinc-500", "Loading stats…"));
    try {
      const stats = await fetchStats(code);
      const clicks = statTile("Clicks", String(stats.clicks));
      clicks.lastChild.classList.add("text-2xl", "font-manrope", "text-[#ef233c]");
      const dest = statTile("Destination", stats.long_url, "sm:col-span-2");
      dest.lastChild.title = stats.long_url;
      statsPanel.replaceChildren(clicks, dest);
    } catch (err) {
      statsPanel.replaceChildren(el("div", "sm:col-span-3 text-red-300", err.message));
    }
  }

  // ---------- Recent links (per-browser convenience only) ----------

  function loadRecent() {
    try {
      const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function saveRecent(items) {
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(items.slice(0, RECENT_LIMIT)));
    } catch (_) {
      /* storage unavailable: recent list just won't persist */
    }
  }

  function addRecent(entry) {
    const items = loadRecent().filter((item) => item.code !== entry.code);
    items.unshift(entry);
    saveRecent(items);
    renderRecent();
  }

  function removeRecent(code) {
    saveRecent(loadRecent().filter((item) => item.code !== code));
    renderRecent();
  }

  function iconButton(name, label, onClick) {
    const btn = el("button", "inline-flex items-center justify-center w-9 h-9 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-colors");
    btn.type = "button";
    btn.title = label;
    btn.setAttribute("aria-label", label);
    btn.appendChild(icon(name));
    btn.addEventListener("click", onClick);
    return btn;
  }

  function renderRecent() {
    const items = loadRecent();
    recentWrap.classList.toggle("hidden", items.length === 0);
    recentList.replaceChildren(
      ...items.map((item) => {
        const li = el("li", "flex items-center gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors");

        const text = el("div", "min-w-0 flex-1");
        const link = el("a", "block font-medium text-white hover:text-[#ef233c] transition-colors truncate", shortDisplay(item.code));
        link.href = shortHref(item.code);
        link.target = "_blank";
        link.rel = "noopener";
        const long = el("div", "text-xs text-zinc-500 truncate", item.longUrl);
        long.title = item.longUrl;
        text.append(link, long);

        const actions = el("div", "flex items-center shrink-0");
        actions.append(
          iconButton("lucide:copy", "Copy short link", () => copyText(shortHref(item.code))),
          iconButton("lucide:bar-chart-3", "View stats", () => {
            renderResult(item);
            showStats(item.code);
            result.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }),
          iconButton("lucide:trash-2", "Remove from list", () => removeRecent(item.code))
        );

        li.append(text, actions);
        return li;
      })
    );
  }

  // ---------- Events ----------

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitBtn.disabled) return;
    clearError();

    const longUrl = normalizeUrl(input.value);
    if (!longUrl) {
      showError("That doesn't look like a valid link. Try something like https://example.com/page");
      input.focus();
      return;
    }

    setLoading(true);
    try {
      const data = await shortenUrl(longUrl);
      const entry = { code: data.code, longUrl, createdAt: Date.now() };
      renderResult(entry);
      addRecent(entry);
      input.value = "";
    } catch (err) {
      showError(err.message, err.retryAfter);
    } finally {
      setLoading(false);
    }
  }

  function goToShortener() {
    $("#shorten").scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => input.focus({ preventScroll: true }), 450);
  }

  form.addEventListener("submit", handleSubmit);
  input.addEventListener("input", clearError);

  resultCopy.addEventListener("click", () => current && copyText(shortHref(current.code)));
  resultStats.addEventListener("click", () => current && showStats(current.code));

  $("#recent-clear").addEventListener("click", () => {
    saveRecent([]);
    renderRecent();
  });

  document.querySelectorAll("[data-get-started]").forEach((btn) => {
    btn.addEventListener("click", goToShortener);
  });

  // The bottom CTA hands its value to the main shortener and submits there.
  $("#cta-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const ctaInput = $("#cta-input");
    input.value = ctaInput.value;
    ctaInput.value = "";
    goToShortener();
    if (input.value.trim()) form.requestSubmit();
  });

  document.querySelectorAll("[data-api-docs]").forEach((a) => {
    a.href = API_BASE + "/docs";
  });
  const curlBase = $("#curl-base");
  if (curlBase) curlBase.textContent = API_BASE;
  $("#year").textContent = String(new Date().getFullYear());

  // Scroll reveals
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((node) => observer.observe(node));
  } else {
    reveals.forEach((node) => node.classList.add("is-visible"));
  }

  renderRecent();
})();

/*!
 * live-metrics.js — refresh the star / citation badges in the visitor's browser.
 *
 * Every badge is server-rendered from _data/github_stars.yml and
 * _data/citations.yml, so the page is already correct without JavaScript. This
 * script only tries to do better: it asks GitHub and Google Scholar for the
 * current numbers and rewrites the badges in place. Anything that fails — no
 * network, a rate limit, a Scholar CAPTCHA — leaves the baked-in number alone.
 *
 * Google Scholar is the only accepted citation source. It serves no CORS header
 * and has no public API, so the profile page is pulled through a public CORS
 * proxy; when no proxy gets through, the badge simply keeps its synced value.
 * Results are cached in localStorage so a visitor clicking through several pages
 * costs one round of requests, not one per page.
 */
(function () {
  "use strict";

  var CFG = window.LIVE_METRICS || {};
  var TTL_MS = 6 * 60 * 60 * 1000; // re-check at most every 6 hours per visitor
  var STARS_CACHE = "lm.stars.v1";
  var CITES_CACHE = "lm.cites.v1";
  var SCHOLAR_PROXIES = [
    function (url) { return "https://api.allorigins.win/raw?url=" + encodeURIComponent(url); },
    function (url) { return "https://api.codetabs.com/v1/proxy?quest=" + encodeURIComponent(url); }
  ];

  // --- tiny helpers ---------------------------------------------------------

  function readCache(name) {
    try {
      var raw = window.localStorage.getItem(name);
      if (!raw) return null;
      var box = JSON.parse(raw);
      if (!box || typeof box.at !== "number" || !box.data) return null;
      return { fresh: Date.now() - box.at < TTL_MS, data: box.data };
    } catch (e) {
      return null;
    }
  }

  function writeCache(name, data) {
    try {
      window.localStorage.setItem(name, JSON.stringify({ at: Date.now(), data: data }));
    } catch (e) {
      /* private mode / quota — the badges still work, just without caching */
    }
  }

  function setBadge(el, value, titleSuffix) {
    var slot = el.querySelector(".metric__count");
    if (!slot || !isFinite(value)) return;
    if (slot.textContent !== String(value)) slot.textContent = String(value);
    el.setAttribute("title", value + " " + titleSuffix);
  }

  function getJSON(url) {
    return fetch(url, { headers: { Accept: "application/vnd.github+json" } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(r.status)); });
  }

  // --- GitHub stars ---------------------------------------------------------

  function applyStars(counts) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-star-repo]"), function (el) {
      var n = counts[el.getAttribute("data-star-repo")];
      if (typeof n === "number") setBadge(el, n, "GitHub stars");
    });
  }

  function refreshStars() {
    var nodes = document.querySelectorAll("[data-star-repo]");
    if (!nodes.length) return;

    var cached = readCache(STARS_CACHE);
    if (cached) applyStars(cached.data);
    if (cached && cached.fresh) return;

    var repos = [];
    Array.prototype.forEach.call(nodes, function (el) {
      var r = el.getAttribute("data-star-repo");
      if (r && repos.indexOf(r) === -1) repos.push(r);
    });

    // Start from the cached map so one failing repo does not drop the others.
    var counts = cached ? Object.assign({}, cached.data) : {};
    Promise.all(repos.map(function (repo) {
      return getJSON("https://api.github.com/repos/" + repo)
        .then(function (d) {
          if (typeof d.stargazers_count === "number") counts[repo] = d.stargazers_count;
        })
        .catch(function () { /* rate-limited or offline; keep whatever we have */ });
    })).then(function () {
      applyStars(counts);
      if (Object.keys(counts).length) writeCache(STARS_CACHE, counts);
    });
  }

  // --- Google Scholar citations --------------------------------------------

  function normalize(s) {
    return String(s).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function bigrams(s) {
    var out = [];
    for (var i = 0; i < s.length - 1; i++) out.push(s.slice(i, i + 2));
    return out;
  }

  /* Dice coefficient — tolerates the small capitalisation/punctuation drift
     between the title stored at sync time and the row Scholar serves today. */
  function similarity(a, b) {
    if (a === b) return 1;
    var A = bigrams(a), B = bigrams(b);
    if (!A.length || !B.length) return 0;
    var seen = Object.create(null), hits = 0;
    A.forEach(function (g) { seen[g] = (seen[g] || 0) + 1; });
    B.forEach(function (g) { if (seen[g] > 0) { seen[g]--; hits++; } });
    return (2 * hits) / (A.length + B.length);
  }

  function parseScholar(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var rows = doc.querySelectorAll(".gsc_a_tr");
    var out = [];
    Array.prototype.forEach.call(rows, function (row) {
      var titleEl = row.querySelector(".gsc_a_at");
      var countEl = row.querySelector(".gsc_a_ac");
      if (!titleEl) return;
      var raw = countEl ? countEl.textContent.trim() : "";
      out.push({ title: normalize(titleEl.textContent), n: raw ? parseInt(raw, 10) : 0 });
    });
    return out;
  }

  function matchToKeys(rows) {
    var titles = CFG.scholarTitles || {};
    var counts = {};
    Object.keys(titles).forEach(function (key) {
      var want = normalize(titles[key]);
      var best = null, bestScore = 0;
      rows.forEach(function (row) {
        var score = similarity(want, row.title);
        if (score > bestScore) { best = row; bestScore = score; }
      });
      if (best && bestScore >= 0.85 && isFinite(best.n)) counts[key] = best.n;
    });
    return counts;
  }

  function applyCites(counts) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-cite-key]"), function (el) {
      var n = counts[el.getAttribute("data-cite-key")];
      if (typeof n === "number" && n > 0) setBadge(el, n, "Google Scholar citations");
    });
  }

  function fetchViaProxies(url, i) {
    i = i || 0;
    if (i >= SCHOLAR_PROXIES.length) return Promise.reject(new Error("no proxy available"));
    return fetch(SCHOLAR_PROXIES[i](url))
      .then(function (r) { return r.ok ? r.text() : Promise.reject(new Error(r.status)); })
      .then(function (text) {
        // A CAPTCHA / consent interstitial comes back 200 but has no result rows.
        if (text.indexOf("gsc_a_tr") === -1) throw new Error("no scholar rows");
        return text;
      })
      .catch(function () { return fetchViaProxies(url, i + 1); });
  }

  function refreshCites() {
    // Off unless site.live_scholar_citations is set: Scholar answers a CAPTCHA to
    // every public CORS proxy, so leaving it on only buys the visitor two futile
    // requests. The synced counts are already correct.
    if (!CFG.liveScholar) return;
    if (!document.querySelector("[data-cite-key]")) return;
    if (!CFG.scholarUser || !CFG.scholarTitles) return;

    var cached = readCache(CITES_CACHE);
    if (cached) applyCites(cached.data);
    if (cached && cached.fresh) return;

    var url = "https://scholar.google.com/citations?hl=en&view_op=list_works&sortby=pubdate" +
      "&pagesize=100&user=" + encodeURIComponent(CFG.scholarUser);

    fetchViaProxies(url)
      .then(function (html) {
        var counts = matchToKeys(parseScholar(html));
        if (!Object.keys(counts).length) return; // parsed nothing we recognise
        applyCites(counts);
        writeCache(CITES_CACHE, counts);
      })
      .catch(function () { /* Scholar unreachable; the synced numbers stand */ });
  }

  function run() {
    if (!window.fetch || !window.Promise || !window.DOMParser) return;
    refreshStars();
    refreshCites();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();

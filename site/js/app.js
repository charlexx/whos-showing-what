// Radar — client-side app
(function () {
  "use strict";

  // ==================== Theme Toggle ====================
  var themeToggle = document.getElementById("theme-toggle");

  function getPreferredTheme() {
    var stored = localStorage.getItem("radar-theme");
    if (stored) return stored;
    return "light";
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    if (themeToggle) {
      themeToggle.textContent = theme === "dark" ? "\u263E" : "\u2600";
    }
  }

  applyTheme(getPreferredTheme());

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      var next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem("radar-theme", next);
    });
  }

  // ==================== Data ====================
  var data = typeof WSW_DATA !== "undefined" ? WSW_DATA : { exhibitions: [], artists: [], venues: [] };

  var artistMap = {};
  data.artists.forEach(function (a) { artistMap[a.id] = a; });

  var venueMap = {};
  data.venues.forEach(function (v) { venueMap[v.id] = v; });

  // ==================== DOM refs ====================
  var grid = document.getElementById("exhibition-grid");
  var emptyState = document.getElementById("empty-state");
  var heroStats = document.getElementById("hero-stats");
  var filterCount = document.getElementById("filter-count");
  var searchInput = document.getElementById("filter-search");
  var selStatus = document.getElementById("filter-status");
  var selCity = document.getElementById("filter-city");
  var selCountry = document.getElementById("filter-country");
  var selRegion = document.getElementById("filter-region");
  var selType = document.getElementById("filter-type");
  var selAdmission = document.getElementById("filter-admission");
  var selMedium = document.getElementById("filter-medium");
  var selFocus = document.getElementById("filter-focus");

  var timePills = document.querySelectorAll(".time-pill");
  var activeTimePill = null;

  var filterToggle = document.getElementById("filter-toggle");
  var filterRowSecondary = document.getElementById("filter-row-secondary");
  var secondaryFilters = [selRegion, selType, selAdmission, selMedium, selFocus];

  var allFilters = [selStatus, selCity, selCountry, selRegion, selType, selAdmission, selMedium, selFocus];

  // ==================== Helpers ====================
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function parseDate(s) {
    var p = s.split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  function formatDate(s) {
    if (!s) return "";
    var d = parseDate(s);
    return d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear();
  }

  function deriveStatus(exh) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var start = parseDate(exh.start_date);
    var end = parseDate(exh.end_date);
    if (today < start) return "upcoming";
    if (today > end) return "past";
    return "current";
  }

  function resolveArtists(ids) {
    if (!ids || !ids.length) return "";
    return ids.map(function (id) {
      var a = artistMap[id];
      return a ? a.name : id;
    }).join(", ");
  }

  function resolveVenue(id) {
    var v = venueMap[id];
    return v ? v.name : id;
  }

  function esc(str) {
    if (!str) return "";
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  function capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // ==================== Time Filter Logic ====================
  function getDateOnly(d) {
    var r = new Date(d.getTime());
    r.setHours(0, 0, 0, 0);
    return r;
  }

  function rangesOverlap(exhStart, exhEnd, rangeStart, rangeEnd) {
    return exhStart <= rangeEnd && exhEnd >= rangeStart;
  }

  function matchesTimeFilter(exh, timeKey) {
    if (!timeKey) return true;
    var today = getDateOnly(new Date());
    var exhStart = parseDate(exh.start_date);
    var exhEnd = parseDate(exh.end_date);

    if (timeKey === "today") {
      return exhStart <= today && exhEnd >= today;
    }
    if (timeKey === "tomorrow") {
      var tom = new Date(today.getTime());
      tom.setDate(tom.getDate() + 1);
      return exhStart <= tom && exhEnd >= tom;
    }
    if (timeKey === "this-week") {
      var weekEnd = new Date(today.getTime());
      var dayOfWeek = today.getDay();
      var daysUntilSun = dayOfWeek === 0 ? 0 : 7 - dayOfWeek;
      weekEnd.setDate(weekEnd.getDate() + daysUntilSun);
      return rangesOverlap(exhStart, exhEnd, today, weekEnd);
    }
    if (timeKey === "this-weekend") {
      var dayNow = today.getDay();
      var satOffset = dayNow === 0 ? -1 : 6 - dayNow;
      var sat = new Date(today.getTime());
      sat.setDate(sat.getDate() + satOffset);
      var sun = new Date(sat.getTime());
      sun.setDate(sun.getDate() + 1);
      if (sun < today) return false;
      var wkStart = sat < today ? today : sat;
      return rangesOverlap(exhStart, exhEnd, wkStart, sun);
    }
    if (timeKey === "this-month") {
      var monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
      var monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return rangesOverlap(exhStart, exhEnd, monthStart, monthEnd);
    }
    if (timeKey === "opening-soon") {
      var limit = new Date(today.getTime());
      limit.setDate(limit.getDate() + 14);
      return exhStart > today && exhStart <= limit;
    }
    if (timeKey === "closing-soon") {
      var limit = new Date(today.getTime());
      limit.setDate(limit.getDate() + 14);
      return exhStart <= today && exhEnd >= today && exhEnd <= limit;
    }
    return true;
  }

  function setActiveTimePill(timeKey) {
    activeTimePill = timeKey || null;
    timePills.forEach(function (btn) {
      var isActive = btn.getAttribute("data-time") === activeTimePill;
      if (isActive) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function uniqueSorted(arr) {
    var seen = {};
    return arr.filter(function (v) {
      if (!v || seen[v]) return false;
      seen[v] = true;
      return true;
    }).sort();
  }

  function uniqueCities() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.city; }));
  }

  function uniqueCountries() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.country; }));
  }

  function uniqueRegions() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.region; }));
  }

  function uniqueTypes() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.type; }));
  }

  function uniqueAdmission() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.admission; }));
  }

  function uniqueMediums() {
    var all = [];
    data.exhibitions.forEach(function (e) {
      (e.mediums || []).forEach(function (m) { all.push(m); });
    });
    return uniqueSorted(all);
  }

  function uniqueFocus() {
    return uniqueSorted(data.exhibitions.map(function (e) { return e.focus; }));
  }

  // ==================== Populate filters ====================
  function populateSelect(el, values, labelFn) {
    values.forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = labelFn ? labelFn(v) : v;
      el.appendChild(opt);
    });
  }

  function populateFilters() {
    populateSelect(selStatus, ["current", "upcoming", "past"], capitalize);
    populateSelect(selCity, uniqueCities());
    populateSelect(selCountry, uniqueCountries());
    populateSelect(selRegion, uniqueRegions());
    populateSelect(selType, uniqueTypes(), capitalize);
    populateSelect(selAdmission, uniqueAdmission(), capitalize);
    populateSelect(selMedium, uniqueMediums(), capitalize);
    populateSelect(selFocus, uniqueFocus(), capitalize);
  }

  // ==================== Hero stats ====================
  function renderHeroStats() {
    var total = data.exhibitions.length;
    var artists = data.artists.length;
    var cities = uniqueCities().length;
    heroStats.innerHTML =
      "<span class=\"stat-num\">" + total + "</span> exhibitions" +
      " &middot; <span class=\"stat-num\">" + artists + "</span> artists" +
      " &middot; <span class=\"stat-num\">" + cities + "</span> cities";
  }

  // ==================== URL Params ====================
  var PARAM_MAP = {
    search: searchInput,
    status: selStatus,
    city: selCity,
    country: selCountry,
    region: selRegion,
    type: selType,
    admission: selAdmission,
    medium: selMedium,
    focus: selFocus
  };

  function readParams() {
    var params = new URLSearchParams(window.location.search);
    Object.keys(PARAM_MAP).forEach(function (key) {
      var val = params.get(key);
      if (val) PARAM_MAP[key].value = val;
    });
    var timeParam = params.get("time");
    if (timeParam) {
      setActiveTimePill(timeParam);
    }
  }

  function writeParams() {
    var params = new URLSearchParams();
    Object.keys(PARAM_MAP).forEach(function (key) {
      var val = PARAM_MAP[key].value;
      if (val) params.set(key, val);
    });
    if (activeTimePill) params.set("time", activeTimePill);
    var qs = params.toString();
    var url = window.location.pathname + (qs ? "?" + qs : "");
    history.replaceState(null, "", url);
  }

  // ==================== Sort ====================
  function sortExhibitions(list) {
    if (activeTimePill === "closing-soon") {
      return list.slice().sort(function (a, b) {
        return a.end_date.localeCompare(b.end_date);
      });
    }
    var statusOrder = { current: 0, upcoming: 1, past: 2 };
    return list.slice().sort(function (a, b) {
      var sa = statusOrder[a._status] || 1;
      var sb = statusOrder[b._status] || 1;
      if (sa !== sb) return sa - sb;
      if (a._status === "past") {
        return b.end_date.localeCompare(a.end_date);
      }
      return a.start_date.localeCompare(b.start_date);
    });
  }

  // ==================== Filter ====================
  function filterExhibitions() {
    var q = searchInput.value.toLowerCase().trim();
    var fStatus = selStatus.value;
    var fCity = selCity.value;
    var fCountry = selCountry.value;
    var fRegion = selRegion.value;
    var fType = selType.value;
    var fAdmission = selAdmission.value;
    var fMedium = selMedium.value;
    var fFocus = selFocus.value;

    return data.exhibitions.filter(function (exh) {
      exh._status = deriveStatus(exh);

      if (fStatus && exh._status !== fStatus) return false;
      if (activeTimePill && !matchesTimeFilter(exh, activeTimePill)) return false;
      if (fCity && exh.city !== fCity) return false;
      if (fCountry && exh.country !== fCountry) return false;
      if (fRegion && exh.region !== fRegion) return false;
      if (fType && exh.type !== fType) return false;
      if (fAdmission && exh.admission !== fAdmission) return false;
      if (fFocus && exh.focus !== fFocus) return false;
      if (fMedium) {
        if (!(exh.mediums || []).some(function (m) { return m === fMedium; })) return false;
      }

      if (q) {
        var artistNames = resolveArtists(exh.artist_ids).toLowerCase();
        var venueName = resolveVenue(exh.venue_id).toLowerCase();
        var title = (exh.title || "").toLowerCase();
        if (title.indexOf(q) === -1 && artistNames.indexOf(q) === -1 && venueName.indexOf(q) === -1) {
          return false;
        }
      }

      return true;
    });
  }

  // ==================== Render ====================
  function renderCard(exh) {
    var status = exh._status;
    var artistNames = resolveArtists(exh.artist_ids);
    var venueName = resolveVenue(exh.venue_id);
    var dateRange = formatDate(exh.start_date) + " \u2013 " + formatDate(exh.end_date);

    var card = document.createElement("article");
    card.className = "card";
    card.setAttribute("role", "listitem");
    card.setAttribute("data-id", exh.id);

    // Header
    var header = "<div class=\"card-header\">" +
      "<h3 class=\"card-title\"><a class=\"card-title-link\" href=\"exhibition/" + encodeURIComponent(exh.id) + ".html\">" + esc(exh.title) + "</a></h3>" +
      "<span class=\"card-toggle\" aria-hidden=\"true\">" +
        "<svg width=\"14\" height=\"14\" viewBox=\"0 0 14 14\" fill=\"none\"><path d=\"M3.5 5.25L7 8.75L10.5 5.25\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>" +
      "</span>" +
    "</div>";

    // Artists
    var artistsHtml = artistNames
      ? "<p class=\"card-artists\">" + esc(artistNames) + "</p>"
      : "";

    // Meta
    var meta = "<div class=\"card-meta\">" +
      "<span class=\"card-venue\">" + esc(venueName) + "</span>" +
      "<span>" + esc(exh.city + ", " + exh.country) + "</span>" +
      "<span>" + esc(dateRange) + "</span>" +
    "</div>";

    // Badges
    var badges = "<div class=\"card-badges\">" +
      "<span class=\"badge badge-status " + esc(status) + "\">" + esc(status) + "</span>" +
      "<span class=\"badge badge-type\">" + esc(exh.type) + "</span>" +
      "<span class=\"badge badge-admission" + (exh.admission === "free" ? " free" : "") + "\">" + esc(exh.admission) + "</span>" +
      (exh.focus ? "<span class=\"badge badge-focus " + esc(exh.focus) + "\">" + esc(exh.focus) + "</span>" : "") +
    "</div>";

    // Mediums
    var mediums = "";
    if (exh.mediums && exh.mediums.length) {
      mediums = "<div class=\"card-mediums\">" +
        exh.mediums.map(function (m) {
          return "<span class=\"medium-tag\">" + esc(m) + "</span>";
        }).join("") +
      "</div>";
    }

    // Expanded body
    var body = "<div class=\"card-body\">";
    if (exh.description) {
      body += "<p class=\"card-description\">" + esc(exh.description) + "</p>";
    }
    body += "<div class=\"card-body-links\">";
    body += "<a class=\"card-detail-link\" href=\"exhibition/" + encodeURIComponent(exh.id) + ".html\">" +
      "View details <span>\u2192</span></a>";
    if (exh.url) {
      body += "<a class=\"card-link\" href=\"" + esc(exh.url) + "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
        "Visit exhibition <span class=\"card-link-arrow\">\u2192</span>" +
      "</a>";
    }
    body += "</div>";
    body += "</div>";

    card.innerHTML = header + artistsHtml + meta + badges + mediums + body;
    card.setAttribute("aria-expanded", "false");

    card.addEventListener("click", function (e) {
      if (e.target.closest(".card-link") || e.target.closest(".card-detail-link") || e.target.closest(".card-title-link")) return;
      card.classList.toggle("expanded");
      card.setAttribute("aria-expanded", card.classList.contains("expanded") ? "true" : "false");
    });

    return card;
  }

  function render() {
    var filtered = filterExhibitions();
    var sorted = sortExhibitions(filtered);
    var total = data.exhibitions.length;

    grid.innerHTML = "";

    if (sorted.length === 0) {
      emptyState.hidden = false;
      grid.style.display = "none";
    } else {
      emptyState.hidden = true;
      grid.style.display = "";
      sorted.forEach(function (exh) {
        grid.appendChild(renderCard(exh));
      });
    }

    filterCount.textContent = "Showing " + sorted.length + " of " + total + " exhibitions";
    writeParams();
  }

  // ==================== Editorial Highlights ====================
  var lastChanceEl = document.getElementById("last-chance");
  var justOpenedEl = document.getElementById("just-opened");

  function renderEditorialCard(exh, type) {
    var venueName = resolveVenue(exh.venue_id);
    var dateLabel = type === "closing"
      ? "Closes " + formatDate(exh.end_date)
      : "Opened " + formatDate(exh.start_date);
    var dateClass = type === "closing" ? "closing" : "opened";

    return "<a class=\"editorial-card\" href=\"exhibition/" + encodeURIComponent(exh.id) + ".html\">" +
      "<div class=\"editorial-card-title\">" + esc(exh.title) + "</div>" +
      "<div class=\"editorial-card-venue\">" + esc(venueName) + "</div>" +
      "<div class=\"editorial-card-city\">" + esc(exh.city) + "</div>" +
      "<div class=\"editorial-card-date " + dateClass + "\">" + esc(dateLabel) + "</div>" +
    "</a>";
  }

  function renderEditorials() {
    var today = getDateOnly(new Date());
    var in7 = new Date(today.getTime());
    in7.setDate(in7.getDate() + 7);
    var ago14 = new Date(today.getTime());
    ago14.setDate(ago14.getDate() - 14);

    var lastChance = [];
    var justOpened = [];

    data.exhibitions.forEach(function (exh) {
      var start = parseDate(exh.start_date);
      var end = parseDate(exh.end_date);
      var isCurrent = start <= today && end >= today;
      if (isCurrent && end <= in7) {
        lastChance.push(exh);
      }
      if (isCurrent && start >= ago14) {
        justOpened.push(exh);
      }
    });

    lastChance.sort(function (a, b) { return a.end_date.localeCompare(b.end_date); });
    justOpened.sort(function (a, b) { return b.start_date.localeCompare(a.start_date); });

    lastChance = lastChance.slice(0, 4);
    justOpened = justOpened.slice(0, 4);

    if (lastChance.length > 0) {
      lastChanceEl.innerHTML = "<div class=\"editorial-section\">" +
        "<div class=\"editorial-label\">Last chance</div>" +
        "<div class=\"editorial-row\">" +
        lastChance.map(function (exh) { return renderEditorialCard(exh, "closing"); }).join("") +
        "</div></div>";
    } else {
      lastChanceEl.innerHTML = "";
    }

    if (justOpened.length > 0) {
      justOpenedEl.innerHTML = "<div class=\"editorial-section\">" +
        "<div class=\"editorial-label\">Just opened</div>" +
        "<div class=\"editorial-row\">" +
        justOpened.map(function (exh) { return renderEditorialCard(exh, "opened"); }).join("") +
        "</div></div>";
    } else {
      justOpenedEl.innerHTML = "";
    }
  }

  // ==================== Filter Toggle ====================
  function getSecondaryActiveCount() {
    var count = 0;
    secondaryFilters.forEach(function (el) {
      if (el.value) count++;
    });
    return count;
  }

  function updateFilterToggle() {
    var count = getSecondaryActiveCount();
    var label = filterToggle.querySelector(".filter-toggle-label");
    var isExpanded = filterRowSecondary.classList.contains("expanded");
    if (isExpanded) {
      label.textContent = "Less filters";
    } else if (count > 0) {
      label.textContent = "More filters (" + count + ")";
    } else {
      label.textContent = "More filters";
    }
    if (count > 0) {
      filterToggle.classList.add("has-active");
    } else {
      filterToggle.classList.remove("has-active");
    }
    if (isExpanded) {
      filterToggle.classList.add("expanded");
    } else {
      filterToggle.classList.remove("expanded");
    }
  }

  function toggleSecondaryFilters() {
    filterRowSecondary.classList.toggle("expanded");
    var isExpanded = filterRowSecondary.classList.contains("expanded");
    filterToggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    updateFilterToggle();
  }

  // ==================== Init ====================
  function init() {
    populateFilters();
    renderHeroStats();
    renderEditorials();
    readParams();

    // Auto-expand secondary row if URL params set any secondary filter
    if (getSecondaryActiveCount() > 0) {
      filterRowSecondary.classList.add("expanded");
      filterToggle.setAttribute("aria-expanded", "true");
    }
    updateFilterToggle();

    render();

    allFilters.forEach(function (el) {
      el.addEventListener("change", function () {
        if (el === selStatus && selStatus.value) {
          setActiveTimePill(null);
        }
        updateFilterToggle();
        render();
      });
    });
    searchInput.addEventListener("input", render);

    filterToggle.addEventListener("click", toggleSecondaryFilters);

    timePills.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-time");
        if (activeTimePill === key) {
          setActiveTimePill(null);
        } else {
          setActiveTimePill(key);
          selStatus.value = "";
        }
        render();
      });
    });

  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

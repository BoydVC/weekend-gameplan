(function () {
  "use strict";

  const TZ = "America/New_York";
  const VIEWS = ["home", "plans", "weather", "about"];
  const KIND_LABEL = {
    fishing: "Fishing",
    trails: "Trails",
    wildlife: "Wildlife",
  };

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  let DATA = window.__DATA__;
  let kidsMode = false;

  function etParts(dt) {
    const fmt = new Intl.DateTimeFormat("en-US", {
      timeZone: TZ,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      weekday: "short",
    });
    const map = {};
    for (const p of fmt.formatToParts(dt)) {
      if (p.type !== "literal") map[p.type] = p.value;
    }
    let h = Number(map.hour);
    if (h === 24) h = 0;
    return {
      Y: Number(map.year),
      M: Number(map.month),
      D: Number(map.day),
      h,
      m: Number(map.minute),
      s: Number(map.second),
      weekday: map.weekday,
    };
  }

  function fmtClock(dt) {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: TZ,
      weekday: "short",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }).format(dt);
  }

  function fmtFetched(iso) {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat("en-US", {
        timeZone: TZ,
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  }

  function hmFromIsoLocal(iso) {
    if (!iso) return "—";
    // "2026-10-16T07:14" or with seconds
    const m = String(iso).match(/T(\d{2}):(\d{2})/);
    if (!m) return iso;
    let h = Number(m[1]);
    const min = m[2];
    const ap = h >= 12 ? "PM" : "AM";
    h = h % 12;
    if (h === 0) h = 12;
    return `${h}:${min} ${ap}`;
  }

  function tideTime(t) {
    // "2026-10-16 18:48"
    const hm = t.split(" ")[1] || t;
    const [H, M] = hm.split(":").map(Number);
    const ap = H >= 12 ? "PM" : "AM";
    let h = H % 12;
    if (h === 0) h = 12;
    return `${h}:${String(M).padStart(2, "0")} ${ap}`;
  }

  function scoreClass(sc) {
    if (sc >= 60) return "";
    if (sc >= 40) return "mid";
    return "low";
  }

  function currentPlans() {
    if (!DATA) return [];
    return kidsMode ? DATA.plans_kids || DATA.plans : DATA.plans || [];
  }

  function currentBackup() {
    if (!DATA) return null;
    return kidsMode ? DATA.backup_kids || DATA.backup : DATA.backup;
  }

  function renderChips() {
    const box = $("#dayChips");
    if (!box || !DATA) return;
    const days = DATA.days || [];
    box.innerHTML = days
      .map((d) => {
        const wx = d.weather || {};
        const sc = d.score || 0;
        return `<div class="day-chip${d.rainy ? " rainy" : ""}">
          <div class="icon">${wx.icon || "🌡️"}</div>
          <div>
            <div class="name"><span class="score-dot ${scoreClass(sc)}"></span>${d.weekday}</div>
            <div class="meta">${wx.label || "—"} · ${wx.precip_prob ?? "—"}% rain · score ${sc}</div>
          </div>
          <div class="temps">${wx.temp_max_f != null ? Math.round(wx.temp_max_f) : "—"}° / ${
          wx.temp_min_f != null ? Math.round(wx.temp_min_f) : "—"
        }°</div>
        </div>`;
      })
      .join("");
  }

  function planCardHTML(p, detailed) {
    const wx = p.weather || {};
    const spot = p.spot || {};
    const tides = (p.tides || [])
      .map(
        (e) =>
          `<span class="tide-chip ${e.type}">${e.type === "H" ? "High" : "Low"} ${tideTime(
            e.t
          )} · ${e.v} ft</span>`
      )
      .join("");
    const alts = (p.alternates || [])
      .map((a) => `<li><strong>${a.name}</strong> — ${a.area} · ${a.drive_min} min</li>`)
      .join("");

    if (!detailed) {
      return `<article class="panel plan-card" data-kind="${p.kind}">
        <span class="kind-pill">${KIND_LABEL[p.kind] || p.kind}</span>
        <p class="plan-day">${p.weekday} · ${p.date}${kidsMode ? " · kids’ pick" : ""}</p>
        <h3>${p.title}</h3>
        <p class="spot-name">${spot.name || "—"}</p>
        <p class="spot-meta">${spot.area || ""} · ~${spot.drive_min ?? "—"} min · ${
        wx.icon || ""
      } ${wx.label || ""}</p>
        <p class="plan-blurb">${p.blurb || spot.why || ""}</p>
        <div class="window-box"><strong>Best window</strong>${p.window || spot.best || "—"}</div>
      </article>`;
    }

    return `<article class="panel plan-card" data-kind="${p.kind}">
      <div class="plan-detail">
        <div>
          <span class="kind-pill">${KIND_LABEL[p.kind] || p.kind}</span>
          <p class="plan-day">${p.weekday} · ${p.date}</p>
          <h3>${p.title}</h3>
          <p class="spot-name">${spot.name || "—"}</p>
          <p class="spot-meta">${spot.area || ""} · ~${spot.drive_min ?? "—"} min drive</p>
          <p class="plan-blurb">${spot.why || ""}</p>
          <p class="plan-blurb">${p.blurb || ""}</p>
          <div class="window-box"><strong>Best window</strong>${p.window || "—"}</div>
          <p class="spot-meta" style="margin-top:.55rem">${spot.tip || ""}</p>
        </div>
        <div>
          <div class="panel-head"><h3>Conditions</h3></div>
          <ul class="facts">
            <li><span>Sky</span><strong>${wx.icon || ""} ${wx.label || "—"}</strong></li>
            <li><span>Temp</span><strong>${
              wx.temp_min_f != null
                ? `${Math.round(wx.temp_min_f)}–${Math.round(wx.temp_max_f)}°F`
                : "—"
            }</strong></li>
            <li><span>Precip</span><strong>${wx.precip_prob ?? "—"}% · ${
      wx.precip_in != null ? wx.precip_in + " in" : "—"
    }</strong></li>
            <li><span>Wind</span><strong>${wx.wind_mph != null ? wx.wind_mph + " mph" : "—"}</strong></li>
            <li><span>Sunset</span><strong>${hmFromIsoLocal(wx.sunset)}</strong></li>
            <li><span>Score</span><strong>${p.score ?? "—"}</strong></li>
          </ul>
          <div class="panel-head" style="margin-top:1rem"><h3>Tides</h3></div>
          <div class="tide-mini">${tides || "<span class='spot-meta'>No extremes</span>"}</div>
          ${
            alts
              ? `<div class="panel-head" style="margin-top:1rem"><h3>Nearby alternates</h3></div><ul class="alt-list">${alts}</ul>`
              : ""
          }
        </div>
      </div>
    </article>`;
  }

  function backupHTML(b) {
    if (!b) return "";
    const spot = b.spot || {};
    const alts = (b.alternates || [])
      .map((a) => `<li><strong>${a.name}</strong> — ${a.area} · ${a.drive_min} min</li>`)
      .join("");
    return `<div class="backup-grid">
      <div>
        <p class="eyebrow">Plan B</p>
        <h3>${b.title}</h3>
        <p class="plan-blurb">${b.blurb || ""}</p>
        <p class="spot-name" style="margin-top:.65rem">${spot.name || "—"}</p>
        <p class="spot-meta">${spot.area || ""} · ~${spot.drive_min ?? "—"} min · ${
      spot.why || ""
    }</p>
      </div>
      <div>
        <div class="panel-head"><h3>Also good indoors</h3></div>
        <ul class="alt-list">${alts}</ul>
      </div>
    </div>`;
  }

  function renderPlans() {
    const plans = currentPlans();
    const backup = currentBackup();
    const home = $("#homePlans");
    const stack = $("#plansStack");
    if (home) home.innerHTML = plans.map((p) => planCardHTML(p, false)).join("");
    if (stack) stack.innerHTML = plans.map((p) => planCardHTML(p, true)).join("");
    const hb = $("#homeBackup");
    const pb = $("#plansBackup");
    if (hb) hb.innerHTML = backupHTML(backup);
    if (pb) pb.innerHTML = backupHTML(backup);
  }

  function renderWeather() {
    const tbody = $("#wxTable tbody");
    const tideList = $("#tideList");
    if (!DATA || !tbody) return;
    const days = DATA.days || [];
    tbody.innerHTML = days
      .map((d) => {
        const wx = d.weather || {};
        return `<tr>
          <td><strong>${d.weekday}</strong><br><span class="hint">${d.date}</span></td>
          <td>${wx.icon || ""} ${wx.label || "—"}</td>
          <td>${
            wx.temp_max_f != null
              ? `${Math.round(wx.temp_max_f)}° / ${Math.round(wx.temp_min_f)}°F`
              : "—"
          }</td>
          <td>${wx.precip_prob ?? "—"}%<br><span class="hint">${
          wx.precip_in != null ? wx.precip_in + " in" : ""
        }</span></td>
          <td>${wx.wind_mph != null ? wx.wind_mph + " mph" : "—"}</td>
          <td>${hmFromIsoLocal(wx.sunrise)}</td>
          <td>${hmFromIsoLocal(wx.sunset)}</td>
        </tr>`;
      })
      .join("");

    if (tideList) {
      tideList.innerHTML = days
        .map((d) => {
          const rows = (d.tides || [])
            .map(
              (e) =>
                `<span class="tide-chip ${e.type}">${e.type === "H" ? "High" : "Low"} ${tideTime(
                  e.t
                )} · ${e.v} ft</span>`
            )
            .join("");
          return `<div class="tide-day"><h4>${d.weekday} · ${d.date}</h4><div class="tide-rows">${
            rows || "—"
          }</div></div>`;
        })
        .join("");
    }
  }

  function renderAbout() {
    if (!DATA) return;
    $("#aboutSource").textContent = DATA.source || "—";
    $("#aboutFetched").textContent = fmtFetched(DATA.fetched_at);
    $("#aboutLive").textContent = DATA.live ? "Yes · live public APIs" : "No · EXAMPLE demo";
    $("#aboutNote").textContent = DATA.note || "—";
  }

  function renderAll() {
    if (!DATA) {
      $("#dataPill").textContent = "no data";
      $("#dataPill").classList.add("demo");
      $("#demoBanner").hidden = false;
      return;
    }
    const live = !!DATA.live;
    const pill = $("#dataPill");
    pill.textContent = live ? "Live weather + tides" : "Demo / EXAMPLE";
    pill.classList.toggle("live", live);
    pill.classList.toggle("demo", !live);
    $("#demoBanner").hidden = live;

    $("#weekendLabel").textContent = (DATA.weekend && DATA.weekend.label) || "—";
    $("#heroLead").textContent = kidsMode
      ? "Kids’ pick on — Char & Vic friendly parks get priority across the three outing cards."
      : "Three outing plans from weather, sunset, and Annapolis tides — plus a rainy-day backup.";

    renderChips();
    renderPlans();
    renderWeather();
    renderAbout();
    $("#footStatus").textContent = `${DATA.source || "—"} · fetched ${fmtFetched(
      DATA.fetched_at
    )}`;
  }

  function showView(name) {
    if (!VIEWS.includes(name)) name = "home";
    $$(".tab").forEach((btn) => {
      const on = btn.dataset.view === name;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    $$(".view").forEach((el) => {
      const on = el.id === `view-${name}`;
      el.classList.toggle("active", on);
      if (on) el.removeAttribute("hidden");
      else el.setAttribute("hidden", "");
    });
    if (location.hash.replace(/^#/, "") !== name) {
      history.replaceState(null, "", `#${name}`);
    }
  }

  function tickClock() {
    $("#clockPill").textContent = fmtClock(new Date()) + " ET";
  }

  function bind() {
    $$(".tab").forEach((btn) => {
      btn.addEventListener("click", () => showView(btn.dataset.view));
    });
    window.addEventListener("hashchange", () => {
      showView(location.hash.replace(/^#/, "") || "home");
    });
    const kids = $("#kidsPick");
    if (kids) {
      kids.addEventListener("change", () => {
        kidsMode = !!kids.checked;
        renderAll();
      });
    }
  }

  function init() {
    bind();
    tickClock();
    setInterval(tickClock, 1000);
    renderAll();
    showView(location.hash.replace(/^#/, "") || "home");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

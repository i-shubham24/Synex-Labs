"use strict";

const TOKEN = document.querySelector('meta[name="engine-token"]').content;
const REFRESH_MS = 15000;
const OPEN = ["new", "alerted"];
const ACTIVE = ["contacted", "replied", "call_booked", "proposal_sent"];
const CLOSED = ["won", "lost", "no_response", "not_interested", "skipped", "ignored", "disqualified"];
const FILTER_TABS = ["prospects", "leads"];

let state = null;
let tab = "prospects";
let filter = "open";
let nicheFilter = "";
let lastListKey = "";
let lastLogKey = "";
let offline = false;
let timer = null;
let editing = false; // pause list re-render while typing

const $ = (id) => document.getElementById(id);
const n = (v) => (Number.isFinite(v) ? v : 0);

/* ---------- helpers ---------- */

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (k === "value") node.value = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function safeUrl(url, schemes = /^https?:\/\//i) {
  return typeof url === "string" && schemes.test(url) ? url : null;
}

function link(url, text, opts = {}) {
  const safe = safeUrl(url, opts.schemes || /^(https?:\/\/|mailto:|tel:|\/preview\/)/i);
  if (!safe) return null;
  return el("a", { href: safe, target: "_blank", rel: "noopener noreferrer", class: opts.cls || null, onclick: opts.onclick || null }, text);
}

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: { "X-Engine-Token": TOKEN }, cache: "no-store" };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch { /* empty */ }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function act(path, body = null, okText = null) {
  try {
    const res = await api(path, "POST", body);
    toast(okText || res.message || "Done");
    await refresh(true);
    return res;
  } catch (e) {
    toast(e.message);
    return null;
  }
}

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 3200);
}

function duration(seconds) {
  const m = Math.floor(seconds / 60), h = Math.floor(m / 60), d = Math.floor(h / 24);
  if (d) return `${d}d ${h % 24}h`;
  if (h) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

function sqliteDate(value) {
  return value && !value.includes("T") ? value.replace(" ", "T") + "Z" : value;
}

function relative(iso) {
  if (!iso) return "";
  const diff = (new Date(sqliteDate(iso)).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  let text;
  if (abs < 60) text = "under a minute";
  else if (abs < 3570) text = `${Math.round(abs / 60)} min`;
  else if (abs < 86400) text = `${Math.round(abs / 3600)} h`;
  else text = `${Math.round(abs / 86400)} d`;
  return diff >= 0 ? `in ${text}` : `${text} ago`;
}

async function copy(text, what = "Copied") {
  try { await navigator.clipboard.writeText(text); toast(what); }
  catch { toast("Could not copy. Select the text instead."); }
}

function label(stage) { return (state && state.stages.labels[stage]) || stage; }

function stageSelect(current, stages, onChange) {
  const sel = el("select", { class: "stage", onchange: (e) => onChange(e.target.value) },
    stages.map((s) => el("option", { value: s, selected: s === current ? true : null }, label(s))));
  sel.addEventListener("focus", () => { editing = true; });
  sel.addEventListener("blur", () => { editing = false; });
  return sel;
}

function modal(title, body) {
  $("modal-title").textContent = title;
  $("modal-body").replaceChildren(...[body].flat(3).filter(Boolean));
  $("modal").hidden = false;
}
$("modal-close").addEventListener("click", () => { $("modal").hidden = true; });
$("modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("modal").hidden = true; });

function showBrief(name, brief) {
  if (!brief) return toast("No brief yet");
  modal(`Pre-call brief: ${name}`, [
    el("p", {}, brief.summary || ""),
    brief.talking_points?.length ? [el("div", { class: "section-title" }, "Talking points"), el("ul", {}, brief.talking_points.map((x) => el("li", {}, x)))] : null,
    brief.questions?.length ? [el("div", { class: "section-title" }, "Ask them"), el("ul", {}, brief.questions.map((x) => el("li", {}, x)))] : null,
    brief.recommended_package ? el("p", {}, el("b", {}, "Suggest: "), brief.recommended_package) : null,
    brief.price_note ? el("p", { class: "hint" }, brief.price_note) : null,
  ]);
}

/* ---------- header, kpis, health ---------- */

function renderStatus() {
  const s = $("status");
  s.classList.toggle("live", !offline);
  s.classList.toggle("down", offline);
  $("status-text").textContent = offline ? "Offline" : `Running, up ${duration(state.engine.uptime_s)}`;
}

function renderKpis() {
  const st = state.stats;
  const cards = [
    { num: n(st.prospects_no_website), label: n(st.prospects_no_website_india) ? `No website yet (${st.prospects_no_website_india} in India)` : "No website yet", hot: true },
    { num: n(st.prospects_old_site), label: "Old websites to upgrade", hot: true },
    { num: n(st.followups_due), label: "Follow-ups due", hot: n(st.followups_due) > 0 },
    { num: n(st.replies_waiting) + n(st.leads_to_contact), label: "Replies and leads waiting", hot: true },
  ];
  const key = JSON.stringify(cards);
  if (renderKpis._key === key) return;
  renderKpis._key = key;
  $("kpis").replaceChildren(...cards.map((c, i) =>
    el("div", { class: `kpi${c.hot ? " hot" : ""}`, style: `--i:${i}` },
      el("div", { class: "num" }, c.num ?? 0), el("div", { class: "label" }, c.label))));
}

function renderHealth() {
  const h = state.health;
  const items = [
    ["Gemini AI", h.gemini, h.gemini ? "on" : "missing key"],
    ["Telegram", h.telegram, h.telegram ? "on" : "not set"],
    ["Google Places", h.places, h.places ? `${h.places_calls_left} calls left` : "off, free OpenStreetMap"],
    ["Email", h.email, h.email ? `${h.email_left_today} of ${h.email_limit_today} left today` : "off (no SMTP)"],
    ["Inbox", h.inbox, h.inbox ? "watching" : "off"],
    ["Bluesky", h.bluesky, h.bluesky ? "on" : "off"],
    ["Reddit API", h.reddit_oauth, h.reddit_oauth ? "on" : "RSS"],
    ["X login", h.x_login, h.x_login ? "on" : "off"],
  ];
  const nodes = items.map(([name, on, note]) => el("span", { class: `item${on ? " on" : ""}` }, el("i", { class: "sq" }), `${name}: ${note}`));
  nodes.push(el("span", { class: "item targets" }, `Targets: ${h.niches.join(", ")} in ${h.cities.join("; ")}`));
  $("health").replaceChildren(...nodes);
}

/* ---------- prospects ---------- */

function inFilter(item) {
  const status = item.status;
  if (nicheFilter && item.niche !== undefined && item.niche !== nicheFilter) return false;
  if (filter === "all") return true;
  if (filter === "open") return OPEN.includes(status);
  if (filter === "first") return OPEN.includes(status) && item.priority_group === "first";
  if (filter === "upgrade") return OPEN.includes(status) && item.priority_group === "upgrade";
  if (filter === "active") return ACTIVE.includes(status);
  return CLOSED.includes(status);
}

// Business-type dropdown for the Prospects tab, with how many are waiting in each
function renderNicheFilter() {
  const sel = $("niche-filter");
  sel.hidden = tab !== "prospects";
  if (sel.hidden || editing) return;
  const counts = {};
  for (const p of state.prospects) {
    if (OPEN.includes(p.status) && p.niche) counts[p.niche] = (counts[p.niche] || 0) + 1;
  }
  const niches = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const key = JSON.stringify([niches, counts, nicheFilter]);
  if (renderNicheFilter._key === key) return;
  renderNicheFilter._key = key;
  sel.replaceChildren(
    el("option", { value: "" }, "All business types"),
    ...niches.map((n) => el("option", { value: n, selected: n === nicheFilter ? true : null }, `${n} (${counts[n]})`)),
  );
  if (nicheFilter && !counts[nicheFilter]) sel.value = nicheFilter;
}

function chip(text, strong = false) {
  return el("span", { class: `label-tag${strong ? " strong" : ""}` }, text);
}

function prospectChips(p) {
  const out = [];
  if (p.priority_group === "first") out.push(chip("1st · No website", true));
  else if (p.priority_group === "upgrade") out.push(chip("2nd · Old website", true));
  if (p.india) out.push(chip("India"));
  if (p.new_business) out.push(chip("New business"));
  const year = new Date().getFullYear();
  if (p.old5) out.push(chip("5+ years old", true));
  if (p.site_since) out.push(chip(`Online since ${p.site_since}`));
  if (p.last_update_year && p.last_update_year <= year - 3) out.push(chip(`Not updated since ${p.last_update_year}`));
  if (p.established) {
    const c = chip("Busy site");
    if (p.traffic_note) c.title = p.traffic_note;
    out.push(c);
  }
  return out.length ? el("div", { class: "chips-row" }, out) : null;
}

function leadChips(l) {
  const out = [];
  if (l.first_website) out.push(chip("1st · No website", true));
  else if (l.old_website) out.push(chip("2nd · Old website", true));
  if ((l.country || "").toLowerCase().includes("india")) out.push(chip("India"));
  return out.length ? el("div", { class: "chips-row" }, out) : null;
}

function contactButtons(p) {
  const out = [];
  const markOn = (channel) => () => { setTimeout(() => act(`/api/prospect/${p.id}/contacted`, { channel }, "Marked as contacted"), 400); };
  if (p.links.whatsapp) out.push(link(p.links.whatsapp, "WhatsApp", { cls: "btn small primary", onclick: markOn("whatsapp") }));
  if (p.can_email) {
    out.push(el("button", { class: "btn small" + (p.links.whatsapp ? "" : " primary"), type: "button", onclick: () => sendOpenerEmail(p) }, "Send email"));
  } else if (p.links.mailto) {
    out.push(link(p.links.mailto, "Email", { cls: "btn small", onclick: markOn("email") }));
  }
  if (p.links.instagram) out.push(link(p.links.instagram, "Instagram", { cls: "btn small ghost", onclick: () => copy(p.opener, "Opener copied, paste it in the DM") }));
  if (p.links.tel) out.push(link(p.links.tel, "Call", { cls: "btn small ghost" }));
  return out;
}

async function sendOpenerEmail(p) {
  if (!confirm(`Send this email to ${p.email}?\n\nSubject: ${p.subject}\n\n${p.opener}`)) return;
  await act(`/api/prospect/${p.id}/email-opener`, { subject: p.subject, body: p.opener });
}

function pagesRow(p) {
  const pg = p.pages;
  const items = [el("span", { class: "label" }, "Pages")];
  if (!pg.generated) {
    items.push(el("button", { class: "linkbtn", type: "button", onclick: (e) => buildPages(p, e.currentTarget) }, "Make audit + demo"));
    return el("div", { class: "links-row" }, items);
  }
  if (pg.demo) items.push(link(pg.demo, "Demo"));
  if (pg.audit) items.push(link(pg.audit, "Audit"));
  if (pg.live) {
    const url = pg.public_demo || pg.public_audit;
    items.push(el("span", { class: "ok-text" }, "Live"), el("button", { class: "linkbtn", type: "button", onclick: () => copy(url, "Link copied") }, "Copy link"));
  } else if (pg.published) {
    items.push(el("span", { class: "hint" }, "Published, live after you deploy the site"));
  } else if (state.health.site_folder) {
    items.push(el("button", { class: "linkbtn", type: "button", onclick: () => act(`/api/prospect/${p.id}/publish`, null, "Copied to the site. Deploy to make it live.") }, "Publish"));
  }
  items.push(el("button", { class: "linkbtn", type: "button", onclick: (e) => buildPages(p, e.currentTarget) }, "Rebuild"));
  return el("div", { class: "links-row" }, items);
}

async function buildPages(p, btn) {
  btn.disabled = true; btn.textContent = "Building, up to a minute";
  await act(`/api/prospect/${p.id}/pages`, null, "Pages ready");
}

function openerBox(p) {
  return el("div", { class: "opener" },
    el("div", { class: "tag" },
      el("span", {}, p.opener_source === "gemini" ? "AI opener" : "Template opener"),
      el("span", { class: "tag-actions" },
        p.opener_source !== "gemini" && state.health.gemini
          ? el("button", { class: "copy", type: "button", onclick: (e) => writeOpener(p.id, e.currentTarget) }, "Write with AI") : null,
        el("button", { class: "copy", type: "button", onclick: () => copy(p.opener, "Opener copied") }, "Copy"))),
    el("div", {}, p.opener));
}

async function writeOpener(id, btn) {
  btn.disabled = true; btn.textContent = "Writing"; btn.classList.add("working");
  const res = await act(`/api/prospect/${id}/opener`, null, "AI opener ready");
  if (!res) { btn.disabled = false; btn.textContent = "Write with AI"; btn.classList.remove("working"); }
}

function notesBox(p) {
  const box = el("textarea", { class: "notes", rows: "1", placeholder: "Notes", value: p.notes || "" });
  box.addEventListener("focus", () => { editing = true; });
  box.addEventListener("blur", async () => {
    editing = false;
    if ((p.notes || "") !== box.value) { p.notes = box.value; try { await api(`/api/prospect/${p.id}/notes`, "POST", { notes: box.value }); toast("Notes saved"); } catch (e) { toast(e.message); } }
  });
  return box;
}

function salesButtons(p) {
  return [
    el("button", { class: "btn small ghost", type: "button", onclick: async () => {
      if (p.brief) return showBrief(p.name, p.brief);
      const res = await act(`/api/prospect/${p.id}/brief`, null, "Brief ready");
      if (res) showBrief(p.name, res.brief);
    } }, p.brief ? "Brief" : "Make brief"),
    p.pages.proposal
      ? link(p.pages.proposal, "Proposal", { cls: "btn small ghost" })
      : el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${p.id}/proposal`, null, "Proposal ready, open it from the row") }, "Make proposal"),
  ];
}

function prospectRow(p, i) {
  const open = OPEN.includes(p.status);
  const closed = CLOSED.includes(p.status);
  const rating = p.rating ? `${p.rating} (${p.review_count || 0} reviews)` : null;
  const contact = [
    p.phone ? el("span", {}, p.phone) : null,
    p.email ? el("span", {}, p.email + (p.email_status === "bounced" ? " (bounced)" : "")) : null,
    link(p.website, "Website"),
    link(p.maps_url, "Maps"),
  ].filter(Boolean);

  let actions;
  if (open) {
    actions = [
      ...contactButtons(p),
      el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${p.id}/contacted`, null, "Marked as contacted") }, "Contacted"),
      el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${p.id}/stage/skipped`, null, "Skipped") }, "Skip"),
    ];
  } else {
    actions = [
      stageSelect(p.status, state.stages.prospect, (s) => act(`/api/prospect/${p.id}/stage/${s}`)),
      ...(closed ? [] : salesButtons(p)),
    ];
  }
  const meta = [el("span", { class: "tier" }, p.tier_label), ` · ${p.niche} · ${p.city}`, rating ? ` · ${rating}` : ""];
  if (!open) meta.push(` · ${label(p.status)}${p.channel ? " via " + p.channel : ""}`);
  if (p.status === "contacted" && p.next_followup_at) meta.push(` · follow-up ${relative(p.next_followup_at)}`);

  return el("article", { class: `row${closed ? " done" : ""}`, style: `--i:${i}` },
    el("div", { class: "heat" }, p.heat_score, el("small", {}, "heat")),
    el("div", {},
      prospectChips(p),
      el("h3", { class: "name" }, p.name),
      el("div", { class: "meta" }, meta),
      contact.length ? el("div", { class: "contact" }, contact) : null,
      (p.issues || []).length ? el("ul", { class: "issues" }, p.issues.slice(0, 4).map((x) => el("li", {}, x))) : null,
      open ? openerBox(p) : null,
      pagesRow(p),
      open ? null : notesBox(p)),
    el("div", { class: "actions" }, actions));
}

/* ---------- follow-ups ---------- */

function followupRow(p, i) {
  const done = () => act(`/api/prospect/${p.id}/followup/done`, null, "Follow-up logged");
  const buttons = [];
  if (p.followup_links.whatsapp) buttons.push(link(p.followup_links.whatsapp, "WhatsApp", { cls: "btn small primary", onclick: () => setTimeout(done, 400) }));
  if (p.can_email) buttons.push(el("button", { class: "btn small", type: "button", onclick: () => act(`/api/prospect/${p.id}/followup/email`) }, "Email now"));
  else if (p.followup_links.mailto) buttons.push(link(p.followup_links.mailto, "Email", { cls: "btn small", onclick: () => setTimeout(done, 400) }));
  buttons.push(
    el("button", { class: "btn small ghost", type: "button", onclick: done }, "Sent"),
    el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${p.id}/stage/replied`, null, "Marked as replied") }, "Replied"),
    el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${p.id}/followup/stop`) }, "Stop"));
  return el("article", { class: "row", style: `--i:${i}` },
    el("div", { class: "heat" }, p.followup_number, el("small", {}, "follow-up")),
    el("div", {},
      el("h3", { class: "name" }, p.name),
      el("div", { class: "meta" }, `${p.niche} · ${p.city}${p.channel ? " · first contact via " + p.channel : ""} · due ${relative(p.next_followup_at)}`),
      el("div", { class: "opener" },
        el("div", { class: "tag" }, el("span", {}, "Follow-up message"),
          el("button", { class: "copy", type: "button", onclick: () => copy(p.followup_text, "Follow-up copied") }, "Copy")),
        el("div", {}, p.followup_text)),
      p.auto_email ? el("p", { class: "hint" }, "This one is emailed automatically during sending hours.") : null),
    el("div", { class: "actions" }, buttons));
}

/* ---------- inbox ---------- */

function inboxRow(m, i) {
  const draft = el("textarea", { class: "draft", value: m.draft_reply || "", placeholder: "Write a reply" });
  draft.addEventListener("focus", () => { editing = true; });
  draft.addEventListener("blur", () => { editing = false; });
  const buttons = [];
  if (!m.handled && m.label !== "bounce") {
    if (state.health.email) buttons.push(el("button", { class: "btn small primary", type: "button", onclick: () => {
      if (confirm(`Send this reply to ${m.from_addr}?`)) act(`/api/email/${m.id}/send`, { body: draft.value });
    } }, "Send reply"));
    buttons.push(el("button", { class: "btn small ghost", type: "button", onclick: () => copy(draft.value, "Reply copied") }, "Copy"));
    if (m.prospect_id) buttons.push(el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/prospect/${m.prospect_id}/stage/call_booked`, null, "Call booked, brief ready") }, "Call booked"));
    buttons.push(el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/email/${m.id}/handled`) }, "Handled"));
  } else {
    buttons.push(el("div", { class: "state-text" }, m.label === "bounce" ? "bounced" : "handled"));
  }
  return el("article", { class: `row${m.handled ? " done" : ""}`, style: `--i:${i}` },
    el("div", { class: "platform" }, "email"),
    el("div", {},
      el("h3", { class: "name" }, m.prospect_name || m.from_addr),
      el("div", { class: "meta" }, el("span", { class: "label-tag" }, (m.label || "new").replace("_", " ")), `  ${m.from_addr} · ${relative(m.created_at)}`),
      m.summary ? el("p", { class: "hint" }, m.summary) : null,
      el("div", { class: "body-text" }, (m.body || "").slice(0, 1200)),
      !m.handled && m.label !== "bounce" ? [el("div", { class: "section-title" }, "Reply"), draft] : null),
    el("div", { class: "actions" }, buttons));
}

/* ---------- social + website leads ---------- */

function leadRow(l, i) {
  const closed = CLOSED.includes(l.status);
  const meta = [l.project_category, l.budget_indicator !== "Not mentioned" ? l.budget_indicator : null, l.source_channel, relative(l.scraped_at)].filter(Boolean).join(" · ");
  const isWeb = l.platform === "website";
  const actions = [];
  if (isWeb && l.reply_link) actions.push(link(l.reply_link, "Reply by email", { cls: "btn small primary", onclick: () => setTimeout(() => act(`/api/lead/${l.id}/stage/contacted`, null, "Marked as contacted"), 400) }));
  if (OPEN.includes(l.status)) actions.push(el("button", { class: "btn small ghost", type: "button", onclick: () => act(`/api/lead/${l.id}/stage/contacted`, null, "Marked as contacted") }, "Contacted"));
  else actions.push(stageSelect(l.status, state.stages.lead, (s) => act(`/api/lead/${l.id}/stage/${s}`)));
  return el("article", { class: `row${closed ? " done" : ""}`, style: `--i:${i}` },
    el("div", { class: "platform" }, l.platform),
    el("div", {},
      leadChips(l),
      el("h3", { class: "name" }, link(l.url, l.title || "(untitled)", { schemes: /^https?:\/\//i }) || (l.title || "(untitled)")),
      el("div", { class: "meta" }, meta, l.reply_email ? ` · ${l.reply_email}` : ""),
      isWeb && l.content ? el("div", { class: "body-text" }, l.content.slice(0, 900)) : null,
      l.draft_icebreaker ? el("div", { class: "opener" },
        el("div", { class: "tag" }, el("span", {}, isWeb ? "Drafted reply" : "Drafted icebreaker"),
          el("button", { class: "copy", type: "button", onclick: () => copy(l.draft_icebreaker) }, "Copy")),
        el("div", {}, l.draft_icebreaker)) : null),
    el("div", { class: "actions" }, actions));
}

/* ---------- pipeline ---------- */

function renderPipeline() {
  const cols = [
    ["contacted", "Contacted"], ["replied", "Replied"], ["call_booked", "Call booked"],
    ["proposal_sent", "Proposal sent"], ["won", "Won"], ["closed", "Closed"],
  ];
  const items = [
    ...state.pipeline.map((p) => ({ kind: "p", ...p })),
    ...state.leads.filter((l) => [...ACTIVE, "won", "lost", "no_response", "not_interested"].includes(l.status)).map((l) => ({ kind: "l", ...l, name: l.title })),
  ];
  const board = el("div", { class: "board" }, cols.map(([key, title]) => {
    const inCol = items.filter((x) => key === "closed" ? ["lost", "no_response", "not_interested"].includes(x.status) : x.status === key);
    return el("div", { class: "col" },
      el("h3", {}, title, el("span", {}, inCol.length)),
      inCol.map((x, i) => el("div", { class: "card-p", style: `animation-delay:${i * 30}ms` },
        el("b", {}, x.name),
        el("div", { class: "meta" }, x.kind === "p" ? `${x.niche} · ${x.city}${x.channel ? " · " + x.channel : ""}` : `${x.platform} lead`),
        x.kind === "p"
          ? stageSelect(x.status, state.stages.prospect, (s) => act(`/api/prospect/${x.id}/stage/${s}`))
          : stageSelect(x.status, state.stages.lead, (s) => act(`/api/lead/${x.id}/stage/${s}`)),
        x.kind === "p" && ["call_booked", "proposal_sent", "replied"].includes(x.status) ? el("div", { class: "row-actions" }, salesButtons(x)) : null)));
  }));
  return items.length ? board : el("div", { class: "empty" }, "Nothing in the pipeline yet. Contact a prospect to start.");
}

/* ---------- insights ---------- */

function renderInsights() {
  const perf = state.insights.performance;
  const st = state.stats;
  const table = perf.length ? el("table", { class: "insights" },
    el("thead", {}, el("tr", {}, ["Niche", "City", "Found", "Contacted", "Replied+", "Won", "Reply rate"].map((h) => el("th", {}, h)))),
    el("tbody", {}, perf.map((r) => el("tr", {},
      el("td", {}, r.niche), el("td", {}, r.city),
      el("td", { class: "num-cell" }, r.found), el("td", { class: "num-cell" }, r.contacted),
      el("td", { class: "num-cell" }, r.positive), el("td", { class: "num-cell" }, r.won),
      el("td", { class: "num-cell" }, r.reply_rate === null ? "n/a" : `${Math.round(r.reply_rate * 100)}%`))))) : el("p", { class: "hint" }, "No data yet.");
  return el("div", {},
    el("div", { class: "section-title" }, "What is working"), table,
    el("p", { class: "hint" }, "The prospector searches untried niches and cities first, then the ones that earn the most replies."),
    el("div", { class: "section-title" }, "Next searches"),
    el("div", { class: "chips" }, state.insights.next_searches.map((s) => el("span", { class: "chip" }, `${s.niche} · ${s.city}`))),
    el("div", { class: "section-title" }, "Email"),
    el("p", {}, state.health.email
      ? `${st.emails_7d} emails sent in the last 7 days. ${state.health.email_left_today} of ${state.health.email_limit_today} left today (warm-up).`
      : "Email is off. Add SMTP settings in .env to send openers and follow-ups automatically."));
}

/* ---------- Quora / Reddit answer helper ---------- */

const answerState = { question: "", platform: "Quora", answer: "", note: "" };

function renderAnswerHelper() {
  const question = el("textarea", { class: "draft", rows: "5", placeholder: "Paste a Quora or Reddit question here, with any details the person gave", value: answerState.question });
  question.addEventListener("input", () => { answerState.question = question.value; });
  question.addEventListener("focus", () => { editing = true; });
  question.addEventListener("blur", () => { editing = false; });
  const platform = el("select", { class: "stage", onchange: (e) => { answerState.platform = e.target.value; } },
    ["Quora", "Reddit"].map((p) => el("option", { value: p, selected: p === answerState.platform ? true : null }, p)));
  const output = el("textarea", { class: "draft", rows: "9", placeholder: "Your drafted answer appears here", value: answerState.answer });
  output.addEventListener("input", () => { answerState.answer = output.value; });
  output.addEventListener("focus", () => { editing = true; });
  output.addEventListener("blur", () => { editing = false; });
  const note = el("p", { class: "hint" }, answerState.note);
  const btn = el("button", { class: "btn small primary", type: "button", onclick: async () => {
    btn.disabled = true; btn.textContent = "Writing";
    try {
      const res = await api("/api/answer", "POST", { question: answerState.question, platform: answerState.platform });
      answerState.answer = res.answer;
      answerState.note = res.note || (res.link_used ? `Link used: ${res.link_used}` : "");
      output.value = res.answer;
      note.textContent = answerState.note;
    } catch (e) { toast(e.message); }
    btn.disabled = false; btn.textContent = "Draft answer";
  } }, "Draft answer");
  return el("div", {},
    el("p", {}, "Find a question on Quora or Reddit where an Indian business owner asks about websites, paste it here, and post the drafted answer yourself from your own account."),
    el("div", { class: "section-title" }, "Question"), question,
    el("div", { class: "row-actions", style: "display:flex;gap:8px;margin:10px 0" }, platform, btn),
    el("div", { class: "section-title" }, "Answer"), output,
    el("div", { style: "display:flex;gap:8px;margin-top:8px;align-items:center" },
      el("button", { class: "btn small ghost", type: "button", onclick: () => copy(output.value, "Answer copied") }, "Copy"), note),
    el("div", { class: "section-title" }, "How to use Quora well"),
    el("ul", { class: "issues" },
      [
        "Set your profile credential to something like \"Founder, Synex Labs (websites for Indian businesses)\".",
        "Follow topics such as Website Development, Small Business in India, Web Design and Digital Marketing.",
        "Answer 3 to 5 questions a week, like \"website cost in India\", \"best web developer in Delhi\" or \"do I need a website for my shop\".",
        "Be useful first. One link per answer, to the page that fits, such as /websites-for/clinics.",
        "Older questions with many views keep sending visitors for months, so they are worth answering too.",
      ].map((t) => el("li", {}, t))));
}

/* ---------- list dispatcher ---------- */

function renderList(force = false) {
  const st = state.stats;
  $("count-prospects").textContent = st.prospects_to_contact || "";
  $("count-followups").textContent = st.followups_due || "";
  $("count-inbox").textContent = st.replies_waiting || "";
  $("count-leads").textContent = st.leads_to_contact || "";
  $("filters").hidden = !FILTER_TABS.includes(tab);
  renderNicheFilter();
  $("filter-first").hidden = $("filter-upgrade").hidden = tab !== "prospects";
  $("filter-first").textContent = `No website${n(st.prospects_no_website) ? " " + st.prospects_no_website : ""}`;
  $("filter-upgrade").textContent = `Old website${n(st.prospects_old_site) ? " " + st.prospects_old_site : ""}`;
  if (tab !== "prospects" && (filter === "first" || filter === "upgrade")) {
    filter = "open";
    document.querySelectorAll(".filter").forEach((x) => x.classList.toggle("active", x.dataset.filter === "open"));
  }

  let items, render, empty;
  if (tab === "prospects") {
    items = state.prospects.filter(inFilter); render = prospectRow;
    empty = filter === "open" ? "No prospects waiting. Click \"Find prospects now\"."
      : filter === "first" ? "No businesses without a website yet. The next search adds more."
      : filter === "upgrade" ? "No old websites found yet." : "Nothing here yet.";
  } else if (tab === "followups") {
    items = state.followups; render = followupRow; empty = "No follow-ups due. They appear here 3, 7 and 14 days after first contact.";
  } else if (tab === "inbox") {
    items = state.inbox; render = inboxRow;
    empty = state.health.inbox ? "No replies yet." : "Inbox watching is off. Add IMAP settings in .env to sort replies automatically.";
  } else if (tab === "leads") {
    items = state.leads.filter(inFilter); render = leadRow; empty = "No leads here. The engine keeps scanning.";
  }

  const key = JSON.stringify([tab, filter, nicheFilter, tab === "pipeline" ? state.pipeline.map((p) => [p.id, p.status]) : null,
    tab === "insights" ? state.insights : null,
    items ? items.map((x) => [x.id, x.status, x.opener || x.draft_icebreaker || x.draft_reply, x.handled, x.pages && x.pages.generated, x.pages && x.pages.published, x.pages && x.pages.live, x.pages && x.pages.proposal, x.brief ? 1 : 0, x.followup_number]) : null]);
  if (!force && (key === lastListKey || editing)) return;
  lastListKey = key;

  const list = $("list");
  if (tab === "pipeline") return list.replaceChildren(renderPipeline());
  if (tab === "insights") return list.replaceChildren(renderInsights());
  if (tab === "answers") return list.replaceChildren(renderAnswerHelper());
  if (!items.length) return list.replaceChildren(el("div", { class: "empty" }, empty));
  list.replaceChildren(...items.slice(0, 150).map(render));
}

/* ---------- jobs + log ---------- */

function renderJobs() {
  $("jobs").replaceChildren(...state.jobs.map((j) => {
    const last = j.last_end
      ? `Last run ${relative(j.last_end)}${j.last_status ? `, ${j.last_status}` : ""}${j.last_message ? `: ${j.last_message}` : ""}`
      : "Not run yet";
    return el("div", { class: `job${j.running ? " running" : ""}` },
      el("span", { class: "jname" }, j.name),
      el("span", { class: "when" }, j.next_run ? relative(j.next_run) : ""),
      el("span", { class: `last${j.last_status === "error" ? " error" : ""}` }, last));
  }));
  const running = state.jobs.filter((j) => j.running).map((j) => j.id);
  $("busy-bar").hidden = running.length === 0;
  setRunning($("run-social"), running.some((id) => /ingestion|social/.test(id)), "Scanning socials", "Scan socials now");
  setRunning($("run-prospect"), running.includes("maps_prospector_job"), "Finding prospects", "Find prospects now");
}

function setRunning(btn, running, busyText, idleText) {
  btn.classList.toggle("running", running);
  btn.disabled = running;
  btn.textContent = running ? busyText : idleText;
}

function renderLog() {
  const key = state.log.join("\n");
  if (key === lastLogKey) return;
  lastLogKey = key;
  const log = $("log");
  const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 30;
  log.textContent = key || "No activity yet.";
  if (atBottom || !log.dataset.seen) { log.scrollTop = log.scrollHeight; log.dataset.seen = "1"; }
}

function render(force = false) {
  renderStatus(); renderKpis(); renderHealth(); renderList(force); renderJobs(); renderLog();
}

/* ---------- data ---------- */

async function refresh(force = false) {
  let data;
  try {
    data = await api("/api/state");
  } catch {
    offline = true;
    if (state) renderStatus();
    $("offline-title").textContent = "Engine is not running";
    $("offline").hidden = false;
    return;
  }
  state = data;
  if (offline) { offline = false; $("offline").hidden = true; }
  try {
    render(force);
  } catch (e) {
    console.error(e);
    toast("The engine is running an older version. Stop it and start it again from the shortcut.");
  }
}

async function runJob(kind) {
  try {
    const res = await api(`/api/run/${kind}`, "POST");
    toast(res.started ? "Started. Results appear here as they come in." : "Already running.");
  } catch (e) { toast(e.message); }
  setTimeout(() => refresh(), 1200);
}

$("run-social").addEventListener("click", () => runJob("social"));
$("run-prospect").addEventListener("click", () => runJob("prospect"));
document.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", () => runJob(b.dataset.run)));
$("stop").addEventListener("click", async () => {
  if (!confirm("Stop the lead engine? Scans, follow-ups and alerts pause until you start it again from the desktop shortcut.")) return;
  try { await api("/api/stop", "POST"); } catch { /* the process may close before replying */ }
  offline = true; clearInterval(timer);
  $("offline-title").textContent = "Engine stopped";
  $("offline").hidden = false;
  renderStatus();
});

document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => {
  tab = b.dataset.tab;
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === b));
  if (state) renderList(true);
}));
$("niche-filter").addEventListener("change", (e) => { nicheFilter = e.target.value; if (state) renderList(true); });
$("niche-filter").addEventListener("focus", () => { editing = true; });
$("niche-filter").addEventListener("blur", () => { editing = false; });

document.querySelectorAll(".filter").forEach((b) => b.addEventListener("click", () => {
  filter = b.dataset.filter;
  document.querySelectorAll(".filter").forEach((x) => x.classList.toggle("active", x === b));
  if (state) renderList(true);
}));
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && !offline) refresh(); });

refresh(true);
timer = setInterval(() => { if (document.visibilityState === "visible") refresh(); }, REFRESH_MS);

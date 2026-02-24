const state = {
  data: [],
  filtered: [],
  revealAll: false,
  revealedIds: new Set(),
  summary: null,
};

const els = {
  stats: document.getElementById("stats"),
  results: document.getElementById("results"),
  resultTitle: document.getElementById("resultTitle"),
  resultMeta: document.getElementById("resultMeta"),
  toggleAllMask: document.getElementById("toggleAllMask"),
  clearFilters: document.getElementById("clearFilters"),
  q: document.getElementById("q"),
  city: document.getElementById("city"),
  province: document.getElementById("province"),
  sexGender: document.getElementById("sex_gender"),
  ethnicity: document.getElementById("ethnicity"),
  knownAllergy: document.getElementById("known_allergy"),
  organization: document.getElementById("organization"),
  practitioner: document.getElementById("practitioner"),
  encounterType: document.getElementById("encounter_type"),
  setting: document.getElementById("setting"),
  minAge: document.getElementById("min_age"),
  maxAge: document.getElementById("max_age"),
  dateFrom: document.getElementById("date_from"),
  dateTo: document.getElementById("date_to"),
  cardTemplate: document.getElementById("card-template"),
  encounterDialog: document.getElementById("encounterDialog"),
  dialogPatientName: document.getElementById("dialogPatientName"),
  dialogPatientMeta: document.getElementById("dialogPatientMeta"),
  dialogProblemList: document.getElementById("dialogProblemList"),
  dialogAllergies: document.getElementById("dialogAllergies"),
  dialogMeds: document.getElementById("dialogMeds"),
  dialogEncounterList: document.getElementById("dialogEncounterList"),
};

const inputs = [
  els.q,
  els.city,
  els.province,
  els.sexGender,
  els.ethnicity,
  els.knownAllergy,
  els.organization,
  els.practitioner,
  els.encounterType,
  els.setting,
  els.minAge,
  els.maxAge,
  els.dateFrom,
  els.dateTo,
];

function createOption(value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = value;
  return option;
}

function populateSelect(selectEl, values) {
  for (const value of values) {
    selectEl.appendChild(createOption(value));
  }
}

function facetKeys(mapObj) {
  return Object.keys(mapObj || {});
}

function renderStats(summary) {
  const stats = [
    ["Patients", summary.total_patients],
    ["Encounters", summary.total_encounters],
    ["Known Allergies", summary.known_allergy_count],
    ["Organizations", facetKeys(summary.organization_counts).length],
    ["Practitioners", facetKeys(summary.practitioner_counts).length],
  ];

  els.stats.innerHTML = "";
  for (const [k, v] of stats) {
    const div = document.createElement("div");
    div.className = "stat";
    div.innerHTML = `<p class="k">${k}</p><p class="v">${v}</p>`;
    els.stats.appendChild(div);
  }
}

function populateFilters(summary) {
  populateSelect(els.city, facetKeys(summary.city_counts));
  populateSelect(els.province, facetKeys(summary.province_counts));
  populateSelect(els.sexGender, facetKeys(summary.sex_gender_counts));
  populateSelect(els.ethnicity, facetKeys(summary.ethnicity_counts));
  populateSelect(els.organization, facetKeys(summary.organization_counts));
  populateSelect(els.practitioner, facetKeys(summary.practitioner_counts));
  populateSelect(els.encounterType, facetKeys(summary.encounter_type_counts));
  populateSelect(els.setting, facetKeys(summary.setting_counts));
}

function toText(list, fallback = "-") {
  if (!Array.isArray(list) || list.length === 0) return fallback;
  return list.join("; ");
}

function maskText(value, masked) {
  const text = value || "-";
  if (!masked) return text;
  return text.replace(/[A-Za-z0-9]/g, "*");
}

function applyMaskClasses(root, masked) {
  const nodes = root.querySelectorAll(".sensitive");
  for (const node of nodes) {
    node.classList.toggle("masked", masked);
  }
}

function recentEncounterReasons(patient) {
  const items = (patient.encounters || [])
    .slice()
    .sort((a, b) => (b.date || "").localeCompare(a.date || ""))
    .slice(0, 2)
    .map((enc) => `${enc.date || ""}: ${enc.reason_for_visit || enc.title || "Visit"}`);
  return items.length ? items.join(" | ") : "-";
}

function cardForPatient(patient) {
  const frag = els.cardTemplate.content.cloneNode(true);
  const revealed = state.revealAll || state.revealedIds.has(patient.id);
  const masked = !revealed;

  frag.querySelector(".name").textContent = patient.name;
  frag.querySelector(".meta").textContent = `${patient.sex_gender || "Unknown"} | ${patient.ethnicity || "Unknown"}`;

  const chipsEl = frag.querySelector(".chips");
  const chips = [
    `${patient.age ?? "?"} years`,
    `${patient.location?.city || "Unknown"}, ${patient.location?.province || ""}`.trim(),
    `${patient.encounter_count || 0} encounters`,
    patient.known_allergy ? "Known allergy" : "No known allergy",
  ];

  for (const text of chips) {
    const chip = document.createElement("span");
    chip.className = "chip";
    if (text.includes("Known allergy")) chip.classList.add("warn");
    if (text.includes("No known allergy")) chip.classList.add("ok");
    chip.textContent = text;
    chipsEl.appendChild(chip);
  }

  if (patient.search_score) {
    const rel = document.createElement("span");
    rel.className = "chip";
    rel.textContent = `Relevance ${patient.search_score}`;
    chipsEl.appendChild(rel);
  }

  if (patient.matched_fields?.length) {
    const match = document.createElement("span");
    match.className = "chip";
    match.textContent = `Matched: ${patient.matched_fields.join(", ")}`;
    chipsEl.appendChild(match);
  }

  frag.querySelector(".dob").textContent = maskText(patient.date_of_birth, masked);
  frag.querySelector(".address").textContent = maskText(patient.address, masked);
  frag.querySelector(".allergies").textContent = maskText(toText(patient.sections?.allergies), masked);
  frag.querySelector(".meds").textContent = maskText(toText(patient.sections?.medications), masked);
  frag.querySelector(".problem-list").textContent = toText(patient.sections?.problem_list);
  frag.querySelector(".plan").textContent = toText(patient.sections?.plan_of_care);
  frag.querySelector(".orgs").textContent = toText(patient.organizations);
  frag.querySelector(".practs").textContent = toText(patient.practitioners);
  frag.querySelector(".last-encounter").textContent = patient.last_encounter_date || "-";
  frag.querySelector(".enc-reasons").textContent = maskText(recentEncounterReasons(patient), masked);

  applyMaskClasses(frag, masked);

  const eye = frag.querySelector(".eye-btn");
  eye.setAttribute("aria-pressed", String(revealed));
  eye.addEventListener("click", () => {
    if (state.revealedIds.has(patient.id)) {
      state.revealedIds.delete(patient.id);
    } else {
      state.revealedIds.add(patient.id);
    }
    renderResults();
  });

  const viewBtn = frag.querySelector(".view-encounters-btn");
  viewBtn.addEventListener("click", () => openEncounterDialog(patient));

  return frag;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function truncate(value, max = 280) {
  if (!value) return "";
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1).trim()}…`;
}

function renderEncounterItem(encounter, masked) {
  const summary = encounter.summary || {};
  const objectiveHighlights = summary.objective_highlights || [];
  const fullAssessment = encounter.sections?.assessment || "";
  const fullPlan = encounter.sections?.plan || "";
  const fullObjective = encounter.sections?.objective || "";
  const fullSubjective = encounter.sections?.subjective || "";
  const reason = encounter.reason_for_visit || encounter.title || "-";

  const clinicalText = maskText(truncate(summary.clinical_summary || fullAssessment || fullPlan, 320) || "-", masked);
  const planText = maskText(truncate(summary.plan_summary || fullPlan, 260) || "-", masked);
  const safeClinical = escapeHtml(clinicalText);
  const safePlan = escapeHtml(planText);
  const safeReason = escapeHtml(maskText(reason, masked));
  const safeObjectiveList = objectiveHighlights
    .map((line) => `<li>${escapeHtml(maskText(line, masked))}</li>`)
    .join("");

  return `
    <article class="encounter-item" data-date="${escapeHtml(encounter.date || "")}">
      <div class="encounter-top">
        <div>
          <h4>${escapeHtml(encounter.title || "Encounter")}</h4>
          <p>${escapeHtml([encounter.date, encounter.type, encounter.setting].filter(Boolean).join(" · "))}</p>
        </div>
        <span class="chip">${escapeHtml(encounter.time || "Time n/a")}</span>
      </div>
      <div class="encounter-summary">
        <p><strong>Reason:</strong> ${safeReason}</p>
        <p><strong>Clinical Summary:</strong> ${safeClinical}</p>
        <p><strong>Plan Summary:</strong> ${safePlan}</p>
      </div>
      ${safeObjectiveList ? `<ul class="encounter-objective">${safeObjectiveList}</ul>` : ""}
      <details>
        <summary>View Full Note Sections</summary>
        <p><strong>Subjective:</strong> ${escapeHtml(maskText(truncate(fullSubjective, 1400) || "-", masked))}</p>
        <p><strong>Objective:</strong> ${escapeHtml(maskText(truncate(fullObjective, 1400) || "-", masked))}</p>
        <p><strong>Assessment:</strong> ${escapeHtml(maskText(truncate(fullAssessment, 1400) || "-", masked))}</p>
        <p><strong>Plan:</strong> ${escapeHtml(maskText(truncate(fullPlan, 1400) || "-", masked))}</p>
      </details>
    </article>
  `;
}

function openEncounterDialog(patient, highlight) {
  // highlight: string (date) or { date?, section?, preview? }
  if (typeof highlight === "string") highlight = { date: highlight };

  // Auto-reveal sensitive data when opening from a citation source,
  // otherwise the text is masked (asterisks) and highlighting can't work.
  if (highlight && (highlight.section || highlight.preview)) {
    state.revealedIds.add(patient.id);
  }

  const revealed = state.revealAll || state.revealedIds.has(patient.id);
  const masked = !revealed;

  // Clear any leftover highlights from a previous citation deep-link
  for (const mark of els.encounterDialog.querySelectorAll("mark.cite-highlight")) {
    mark.replaceWith(mark.textContent);
  }
  for (const el of els.encounterDialog.querySelectorAll(".highlight-section")) {
    el.classList.remove("highlight-section");
  }
  for (const el of els.encounterDialog.querySelectorAll(".highlighted")) {
    el.classList.remove("highlighted");
  }

  els.dialogPatientName.textContent = patient.name || "Patient";
  els.dialogPatientMeta.textContent = `${patient.sex_gender || "Unknown"} | ${patient.ethnicity || "Unknown"} | ${patient.encounter_count || 0} encounters`;
  els.dialogProblemList.textContent = toText(patient.sections?.problem_list);
  els.dialogAllergies.textContent = maskText(toText(patient.sections?.allergies), masked);
  els.dialogMeds.textContent = maskText(toText(patient.sections?.medications), masked);

  els.dialogAllergies.classList.toggle("masked", masked);
  els.dialogMeds.classList.toggle("masked", masked);

  const encounters = (patient.encounters || [])
    .slice()
    .sort((a, b) => (b.date || "").localeCompare(a.date || ""));

  els.dialogEncounterList.innerHTML = encounters
    .map((enc) => renderEncounterItem(enc, masked))
    .join("");

  if (typeof els.encounterDialog.showModal === "function") {
    els.encounterDialog.showModal();
  } else {
    els.encounterDialog.setAttribute("open", "open");
  }

  if (highlight) {
    setTimeout(() => applyDialogHighlight(highlight), 150);
  }
}

function applyDialogHighlight(hl) {
  const { date, section, preview, query } = hl;

  // -- Patient-summary source (no encounter date) --
  if (!date && section) {
    const sectionMap = {
      "problem list": els.dialogProblemList,
      "allergies": els.dialogAllergies,
      "medications": els.dialogMeds,
      "medication summary": els.dialogMeds,
    };
    const key = Object.keys(sectionMap).find((k) => section.toLowerCase().includes(k));
    if (key) {
      const el = sectionMap[key];
      el.closest("div")?.classList.add("highlight-section");
      tryHighlightText(el, query, preview);
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return;
  }

  // -- Encounter source --
  if (!date) return;
  const item = [...els.dialogEncounterList.querySelectorAll(".encounter-item")]
    .find((el) => el.dataset.date === date);
  if (!item) return;

  item.classList.add("highlighted");

  // Always expand details so we can search the full text
  const details = item.querySelector("details");
  if (details) details.open = true;

  // 1. Try text-level highlighting across the ENTIRE encounter item
  const textFound = tryHighlightText(item, query, preview);

  // 2. If text matching missed, apply section-level highlighting as fallback
  if (!textFound && section) {
    const sectionLower = section.toLowerCase();
    for (const p of item.querySelectorAll("p")) {
      const strong = p.querySelector("strong");
      if (!strong) continue;
      const label = strong.textContent.toLowerCase().replace(/[:\s]+$/g, "");
      if (label === sectionLower || label.includes(sectionLower) || sectionLower.includes(label)) {
        p.classList.add("highlight-section");
        break;
      }
    }
  }

  // 3. Scroll to the most specific highlighted element
  const scrollTarget = item.querySelector(".cite-highlight")
    || item.querySelector(".highlight-section")
    || item;
  setTimeout(() => scrollTarget.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
}

function tryHighlightText(container, query, preview) {
  if (!container) return false;
  if (!query && !preview) return false;

  // Build candidates — prioritise the search query, then fall back to preview fragments
  const candidates = [];

  // 1. The original query/keyword is the most relevant thing to highlight
  if (query) {
    const q = query.trim();
    candidates.push(q);
    // Also try individual multi-word sub-phrases (e.g. "blurred vision" from "patients with blurred vision")
    // Skip very short stop-words
    const words = q.split(/\s+/).filter((w) => w.length >= 4);
    if (words.length > 2) {
      // Try sliding windows of 2-3 words
      for (let len = Math.min(words.length, 3); len >= 2; len--) {
        for (let i = 0; i <= words.length - len; i++) {
          candidates.push(words.slice(i, i + len).join(" "));
        }
      }
    }
  }

  // 2. Preview fragments as fallback — strip leading/trailing ellipsis
  if (preview) {
    const raw = preview.trim().replace(/^…+/, "").replace(/…+$/, "").trim();
    const phrases = raw.split(/[.;,\n]+/).map((p) => p.trim()).filter((p) => p.length >= 8);
    phrases.sort((a, b) => b.length - a.length);
    candidates.push(...phrases.slice(0, 4));
  }

  // Deduplicate and filter
  const seen = new Set();
  const unique = candidates.filter((c) => {
    if (!c || c.length < 4) return false;
    const key = c.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  for (const candidate of unique) {
    const search = candidate.toLowerCase();

    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      // Skip text inside <summary> or <strong> labels
      if (node.parentElement.closest("summary, strong")) continue;

      const text = node.textContent.toLowerCase();
      const idx = text.indexOf(search);
      if (idx < 0) continue;

      // Found a match — split and wrap with <mark>
      const matchNode = idx > 0 ? node.splitText(idx) : node;
      if (candidate.length < matchNode.textContent.length) matchNode.splitText(candidate.length);
      const mark = document.createElement("mark");
      mark.className = "cite-highlight";
      matchNode.parentNode.insertBefore(mark, matchNode);
      mark.appendChild(matchNode);
      return true;
    }
  }
  return false;
}

function updateResultHeader() {
  const total = state.summary?.total_patients ?? state.filtered.length;
  els.resultTitle.textContent = `Patients (${state.filtered.length})`;
  els.resultMeta.textContent = `Showing ${state.filtered.length} of ${total} profiles`;
}

function renderResults() {
  els.results.innerHTML = "";
  updateResultHeader();

  if (!state.filtered.length) {
    const p = document.createElement("p");
    p.className = "panel empty";
    p.textContent = "No patients match your current filters.";
    els.results.appendChild(p);
    return;
  }

  for (const patient of state.filtered) {
    els.results.appendChild(cardForPatient(patient));
  }
}

function currentParams() {
  const params = new URLSearchParams({
    q: els.q.value.trim(),
    city: els.city.value,
    province: els.province.value,
    sex_gender: els.sexGender.value,
    ethnicity: els.ethnicity.value,
    known_allergy: els.knownAllergy.value,
    organization: els.organization.value,
    practitioner: els.practitioner.value,
    encounter_type: els.encounterType.value,
    setting: els.setting.value,
    min_age: els.minAge.value,
    max_age: els.maxAge.value,
    date_from: els.dateFrom.value,
    date_to: els.dateTo.value,
  });
  return params;
}

async function fetchFilteredPatients() {
  const resp = await fetch(`/api/patients?${currentParams().toString()}`);
  const payload = await resp.json();
  state.filtered = payload.results || [];
}

let refreshTimer = null;
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    await fetchFilteredPatients();
    renderResults();
  }, 140);
}

function clearAllFilters() {
  for (const el of inputs) {
    if (el.tagName === "SELECT") {
      el.selectedIndex = 0;
      continue;
    }
    el.value = "";
  }
  els.knownAllergy.value = "all";
  scheduleRefresh();
}

async function boot() {
  const [summaryResp, allPatientsResp] = await Promise.all([
    fetch("/api/summary"),
    fetch("/api/patients"),
  ]);

  const summary = await summaryResp.json();
  const allPatients = await allPatientsResp.json();

  state.summary = summary;
  state.data = allPatients.results || [];
  state.filtered = state.data;

  renderStats(summary);
  populateFilters(summary);
  renderResults();

  for (const input of inputs) {
    input.addEventListener("input", scheduleRefresh);
    input.addEventListener("change", scheduleRefresh);
  }

  els.toggleAllMask.addEventListener("click", () => {
    state.revealAll = !state.revealAll;
    els.toggleAllMask.setAttribute("aria-pressed", String(state.revealAll));
    els.toggleAllMask.querySelector(".toggle-label").textContent =
      state.revealAll ? "Hide All Sensitive Data" : "Reveal All Sensitive Data";
    renderResults();
  });

  els.clearFilters.addEventListener("click", clearAllFilters);
}

boot().catch((error) => {
  console.error(error);
  els.results.innerHTML = `<p class="panel empty">Failed to load explorer data: ${error.message}</p>`;
});

/* ───── Chat Widget ───── */

const chat = {
  toggle: document.getElementById("chatToggle"),
  panel: document.getElementById("chatPanel"),
  messages: document.getElementById("chatMessages"),
  form: document.getElementById("chatForm"),
  input: document.getElementById("chatInput"),
  clear: document.getElementById("chatClear"),
  busy: false,
  pendingSources: [],
};

function chatOpen() {
  return chat.panel.classList.contains("open");
}

function toggleChat() {
  const opening = !chatOpen();
  chat.panel.classList.toggle("open", opening);
  chat.panel.setAttribute("aria-hidden", String(!opening));
  chat.toggle.classList.toggle("open", opening);
  if (opening) chat.input.focus();
}

function addBubble(cls, html) {
  const div = document.createElement("div");
  div.className = `chat-bubble ${cls}`;
  div.innerHTML = html;
  chat.messages.appendChild(div);
  chat.messages.scrollTop = chat.messages.scrollHeight;
  return div;
}

function addChart(b64, caption) {
  const wrap = document.createElement("div");
  wrap.className = "chat-chart";
  const img = document.createElement("img");
  img.src = `data:image/png;base64,${b64}`;
  img.alt = caption;
  wrap.appendChild(img);
  const p = document.createElement("p");
  p.textContent = caption;
  wrap.appendChild(p);
  chat.messages.appendChild(wrap);
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "chat-typing";
  el.id = "chatTyping";
  el.innerHTML = "<span></span><span></span><span></span>";
  chat.messages.appendChild(el);
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("chatTyping");
  if (el) el.remove();
}

function clearChat() {
  chat.pendingSources = [];
  chat.messages.innerHTML = `
    <div class="chat-welcome">
      <p>Hi! I can search patient records, answer clinical questions, and generate charts from encounter data.</p>
      <p class="chat-welcome-hint">Try: "Which patients have diabetes?" or "Chart A1C for Eleanor Voss"</p>
    </div>`;
}

async function sendMessage(text) {
  if (chat.busy || !text.trim()) return;
  chat.busy = true;
  chat.form.querySelector("button").disabled = true;

  // Remove welcome message on first send
  const welcome = chat.messages.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  addBubble("user", escapeHtml(text));
  showTyping();

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!resp.ok) {
      hideTyping();
      addBubble("error", `Server error (${resp.status})`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let eventType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ") && eventType) {
          try {
            const data = JSON.parse(line.slice(6));
            handleSSE(eventType, data);
          } catch { /* skip malformed */ }
          eventType = "";
        }
      }
    }
  } catch (err) {
    hideTyping();
    addBubble("error", `Connection failed: ${escapeHtml(err.message)}`);
  } finally {
    hideTyping();
    chat.busy = false;
    chat.form.querySelector("button").disabled = false;
    chat.input.focus();
  }
}

function handleSSE(type, data) {
  switch (type) {
    case "status":
      hideTyping();
      addBubble("status", escapeHtml(data.text || ""));
      showTyping();
      break;
    case "tool_call": {
      hideTyping();
      const label = data.tool === "chart"
        ? `Generating chart for ${data.patient} — ${data.metric}`
        : `Searching: ${data.query || data.keyword || ""}`;
      addBubble("tool-call", `&#9881; ${escapeHtml(label)}`);
      showTyping();
      break;
    }
    case "sources":
      chat.pendingSources = chat.pendingSources.concat(data.sources || []);
      break;
    case "chart":
      hideTyping();
      addChart(data.b64, `${data.metric} — ${data.patient}`);
      showTyping();
      break;
    case "reply": {
      hideTyping();
      const sources = chat.pendingSources;
      const bubble = addBubble("assistant", formatReply(data.text || "", sources));
      attachCitationClicks(bubble, sources);
      linkPatientNames(bubble);
      if (sources.length) {
        appendCitationBar(bubble, sources);
      }
      chat.pendingSources = [];
      break;
    }
    case "open_timeline":
      openTimelineFromChat(data.patient_name);
      break;
    case "error":
      hideTyping();
      addBubble("error", escapeHtml(data.text || "Unknown error"));
      break;
    case "done":
      hideTyping();
      break;
  }
}

function formatReply(text, sources) {
  let html = escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");

  if (sources && sources.length) {
    html = html.replace(/\[(\d+)\]/g, (match, num) => {
      const idx = parseInt(num) - 1;
      if (idx >= 0 && idx < sources.length) {
        const src = sources[idx];
        const tip = `${src.patient_name} · ${src.section}${src.encounter_date ? " (" + src.encounter_date + ")" : ""}`;
        return `<button class="citation-ref" data-src-idx="${idx}" title="${escapeHtml(tip)}">${match}</button>`;
      }
      return match;
    });
  }
  return html;
}

function attachCitationClicks(bubble, sources) {
  bubble.querySelectorAll(".citation-ref").forEach((btn) => {
    btn.addEventListener("click", () => {
      const src = sources[parseInt(btn.dataset.srcIdx)];
      if (src) openTimelineFromChat(src.patient_name, {
        date: src.encounter_date,
        section: src.section,
        preview: src.preview,
        query: src.query,
      });
    });
  });
}

function appendCitationBar(bubble, sources) {
  const bar = document.createElement("div");
  bar.className = "chat-citations";

  const label = document.createElement("span");
  label.className = "citations-label";
  label.textContent = "Sources:";
  bar.appendChild(label);

  const seen = new Set();
  for (const src of sources) {
    const key = `${src.patient_name}|${src.encounter_date || ""}|${src.section}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const pill = document.createElement("button");
    pill.className = "citation-pill";
    pill.type = "button";

    const num = document.createElement("span");
    num.className = "citation-num";
    num.textContent = src.index;
    pill.appendChild(num);

    const label = src.encounter_date
      ? ` ${src.patient_name} · ${src.section} (${src.encounter_date})`
      : ` ${src.patient_name} · ${src.section}`;
    pill.appendChild(document.createTextNode(label));

    pill.addEventListener("click", () => {
      openTimelineFromChat(src.patient_name, {
        date: src.encounter_date,
        section: src.section,
        preview: src.preview,
        query: src.query,
      });
    });
    bar.appendChild(pill);
  }
  chat.messages.insertBefore(bar, bubble.nextSibling);
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function linkPatientNames(bubble) {
  const names = state.data.map((p) => p.name).filter(Boolean);
  if (!names.length) return;

  const walker = document.createTreeWalker(bubble, NodeFilter.SHOW_TEXT);
  const replacements = [];

  while (walker.nextNode()) {
    const textNode = walker.currentNode;
    // Skip text already inside a button/link
    if (textNode.parentElement.closest("button, a, .citation-ref")) continue;
    for (const name of names) {
      if (textNode.textContent.includes(name)) {
        replacements.push({ textNode, name });
      }
    }
  }

  for (const { textNode, name } of replacements) {
    const parts = textNode.textContent.split(name);
    const frag = document.createDocumentFragment();
    parts.forEach((part, i) => {
      if (i > 0) {
        const btn = document.createElement("button");
        btn.className = "patient-link";
        btn.textContent = name;
        btn.title = `Open encounter timeline for ${name}`;
        btn.addEventListener("click", () => openTimelineFromChat(name));
        frag.appendChild(btn);
      }
      if (part) frag.appendChild(document.createTextNode(part));
    });
    textNode.parentNode.replaceChild(frag, textNode);
  }
}

function openTimelineFromChat(patientName, highlight) {
  const name = (patientName || "").toLowerCase();
  const patient = state.data.find((p) => p.name.toLowerCase() === name);
  if (!patient) {
    addBubble("error", `Patient "${escapeHtml(patientName)}" not found in loaded data.`);
    return;
  }
  openEncounterDialog(patient, highlight || undefined);
}

chat.toggle.addEventListener("click", toggleChat);
chat.clear.addEventListener("click", clearChat);

// Close encounter dialog when clicking outside the dialog panel.
els.encounterDialog.addEventListener("click", (e) => {
  if (!els.encounterDialog.open) return;
  const shell = els.encounterDialog.querySelector(".dialog-shell");
  if (!shell) return;
  const rect = shell.getBoundingClientRect();
  const clickedOutside =
    e.clientX < rect.left ||
    e.clientX > rect.right ||
    e.clientY < rect.top ||
    e.clientY > rect.bottom;
  if (clickedOutside) {
    if (typeof els.encounterDialog.close === "function") {
      els.encounterDialog.close();
    } else {
      els.encounterDialog.removeAttribute("open");
    }
  }
});

chat.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chat.input.value.trim();
  if (!text) return;
  chat.input.value = "";
  sendMessage(text);
});

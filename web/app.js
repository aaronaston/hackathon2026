/* ═══════════════════════════════════════════════
   Patient Intelligence Explorer — Three-Panel App
   ═══════════════════════════════════════════════ */

const state = {
  data: [],
  filtered: [],
  revealAll: false,
  revealedIds: new Set(),
  summary: null,
  selectedPatient: null,
  esSearchInFlight: false,
  esDebounceTimer: null,
};

const els = {
  patientList: document.getElementById("patientList"),
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
  esDropdown: document.getElementById("esDropdown"),
  // Detail panel
  detailEmpty: document.getElementById("detailEmpty"),
  detailContent: document.getElementById("detailContent"),
  detailPatientName: document.getElementById("detailPatientName"),
  detailPatientMeta: document.getElementById("detailPatientMeta"),
  detailProblems: document.getElementById("detailProblems"),
  detailAllergies: document.getElementById("detailAllergies"),
  detailMeds: document.getElementById("detailMeds"),
  detailOrgs: document.getElementById("detailOrgs"),
  detailEncounterList: document.getElementById("detailEncounterList"),
  detailRevealBtn: document.getElementById("detailRevealBtn"),
  // Dialog (for citation deep-links)
  encounterDialog: document.getElementById("encounterDialog"),
  dialogPatientName: document.getElementById("dialogPatientName"),
  dialogPatientMeta: document.getElementById("dialogPatientMeta"),
  dialogProblemList: document.getElementById("dialogProblemList"),
  dialogAllergies: document.getElementById("dialogAllergies"),
  dialogMeds: document.getElementById("dialogMeds"),
  dialogEncounterList: document.getElementById("dialogEncounterList"),
  // Navigation
  navStats: document.getElementById("navStats"),
  middlePanel: document.getElementById("middlePanel"),
  patientListView: document.getElementById("patientListView"),
  filterPanelView: document.getElementById("filterPanelView"),
  activeFilterBadges: document.getElementById("activeFilterBadges"),
};

const inputs = [
  els.q, els.city, els.province, els.sexGender, els.ethnicity,
  els.knownAllergy, els.organization, els.practitioner,
  els.encounterType, els.setting, els.minAge, els.maxAge,
  els.dateFrom, els.dateTo,
];


/* ═══════════════════════════════════════════════
   Icon Navigation
   ═══════════════════════════════════════════════ */

document.querySelectorAll(".icon-nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".icon-nav-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const panel = btn.dataset.panel;
    els.patientListView.classList.toggle("hidden", panel !== "patients");
    els.filterPanelView.classList.toggle("hidden", panel !== "filters");
  });
});


/* ═══════════════════════════════════════════════
   Data Helpers
   ═══════════════════════════════════════════════ */

function createOption(value) {
  const o = document.createElement("option");
  o.value = value; o.textContent = value;
  return o;
}

function populateSelect(sel, values) {
  for (const v of values) sel.appendChild(createOption(v));
}

function facetKeys(m) { return Object.keys(m || {}); }

function toText(list, fallback = "-") {
  if (!Array.isArray(list) || !list.length) return fallback;
  return list.join("; ");
}

function maskText(value, masked) {
  const t = value || "-";
  return masked ? t.replace(/[A-Za-z0-9]/g, "*") : t;
}

function applyMaskClasses(root, masked) {
  for (const n of root.querySelectorAll(".sensitive")) n.classList.toggle("masked", masked);
}

function escapeHtml(v) {
  return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
}

function truncate(v, max = 280) {
  if (!v) return "";
  return v.length <= max ? v : v.slice(0, max - 1).trim() + "…";
}


/* ═══════════════════════════════════════════════
   Nav Stats
   ═══════════════════════════════════════════════ */

function renderNavStats(summary) {
  els.navStats.innerHTML = `
    <div class="nav-stat-group"><div class="nav-stat">${summary.total_patients}</div><div class="nav-stat-label">Patients</div></div>
    <div class="nav-stat-group"><div class="nav-stat">${summary.total_encounters}</div><div class="nav-stat-label">Encounters</div></div>
  `;
}


/* ═══════════════════════════════════════════════
   Patient List (Middle Panel)
   ═══════════════════════════════════════════════ */

function rowForPatient(patient) {
  const row = document.createElement("div");
  row.className = "patient-row";
  if (state.selectedPatient && state.selectedPatient.id === patient.id) {
    row.classList.add("selected");
  }

  const initials = (patient.name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2);

  const allergyChip = patient.known_allergy
    ? `<span class="patient-row-chip warn">Allergy</span>`
    : `<span class="patient-row-chip ok">No allergy</span>`;

  row.innerHTML = `
    <div class="patient-row-avatar">${escapeHtml(initials)}</div>
    <div class="patient-row-info">
      <div class="patient-row-name">${escapeHtml(patient.name)}</div>
      <div class="patient-row-detail">${escapeHtml(patient.sex_gender || "Unknown")} · ${patient.age ?? "?"} yrs · ${escapeHtml(patient.location?.city || "Unknown")}</div>
      <div class="patient-row-chips">
        ${allergyChip}
        ${patient.search_score ? `<span class="patient-row-chip">Score ${patient.search_score}</span>` : ""}
      </div>
    </div>
    <span class="patient-row-count">${patient.encounter_count || 0}</span>
  `;

  row.addEventListener("click", () => selectPatient(patient));
  return row;
}

function renderPatientList() {
  els.patientList.innerHTML = "";
  els.resultMeta.textContent = `${state.filtered.length} of ${state.summary?.total_patients ?? state.filtered.length} patients`;

  if (!state.filtered.length) {
    els.patientList.innerHTML = `<div class="list-empty">No patients match your filters.</div>`;
    return;
  }

  for (const p of state.filtered) {
    els.patientList.appendChild(rowForPatient(p));
  }
}


/* ═══════════════════════════════════════════════
   Detail Panel (Right Panel)
   ═══════════════════════════════════════════════ */

function selectPatient(patient) {
  state.selectedPatient = patient;

  // Update list selection and scroll into view
  for (const row of els.patientList.querySelectorAll(".patient-row")) {
    row.classList.remove("selected");
  }
  const rows = els.patientList.querySelectorAll(".patient-row");
  const idx = state.filtered.indexOf(patient);
  if (idx >= 0 && rows[idx]) {
    rows[idx].classList.add("selected");
    rows[idx].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Show detail panel
  els.detailEmpty.classList.add("hidden");
  els.detailContent.classList.remove("hidden");

  const revealed = state.revealAll || state.revealedIds.has(patient.id);
  const masked = !revealed;

  els.detailPatientName.textContent = patient.name || "Patient";
  els.detailPatientMeta.textContent = `${patient.sex_gender || "Unknown"} · ${patient.ethnicity || "Unknown"} · ${patient.age ?? "?"} years · ${patient.encounter_count || 0} encounters`;
  els.detailProblems.textContent = toText(patient.sections?.problem_list);
  els.detailAllergies.textContent = maskText(toText(patient.sections?.allergies), masked);
  els.detailMeds.textContent = maskText(toText(patient.sections?.medications), masked);
  els.detailOrgs.textContent = toText(patient.organizations);

  els.detailAllergies.classList.toggle("masked", masked);
  els.detailMeds.classList.toggle("masked", masked);

  // Render encounters
  const encounters = (patient.encounters || [])
    .slice()
    .sort((a, b) => (b.date || "").localeCompare(a.date || ""));

  els.detailEncounterList.innerHTML = encounters
    .map((enc) => renderEncounterItem(enc, masked))
    .join("");
}

// Toggle reveal for selected patient
els.detailRevealBtn.addEventListener("click", () => {
  if (!state.selectedPatient) return;
  const id = state.selectedPatient.id;
  if (state.revealedIds.has(id)) state.revealedIds.delete(id);
  else state.revealedIds.add(id);
  selectPatient(state.selectedPatient);
});

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
        <span class="chip">${escapeHtml(encounter.time || "")}</span>
      </div>
      <div class="encounter-summary">
        <p><strong>Reason:</strong> ${escapeHtml(maskText(reason, masked))}</p>
        <p><strong>Clinical:</strong> ${escapeHtml(clinicalText)}</p>
        <p><strong>Plan:</strong> ${escapeHtml(planText)}</p>
      </div>
      ${safeObjectiveList ? `<ul class="encounter-objective">${safeObjectiveList}</ul>` : ""}
      <details>
        <summary>Full Note Sections</summary>
        <p><strong>Subjective:</strong> ${escapeHtml(maskText(truncate(fullSubjective, 1400) || "-", masked))}</p>
        <p><strong>Objective:</strong> ${escapeHtml(maskText(truncate(fullObjective, 1400) || "-", masked))}</p>
        <p><strong>Assessment:</strong> ${escapeHtml(maskText(truncate(fullAssessment, 1400) || "-", masked))}</p>
        <p><strong>Plan:</strong> ${escapeHtml(maskText(truncate(fullPlan, 1400) || "-", masked))}</p>
      </details>
    </article>
  `;
}


/* ═══════════════════════════════════════════════
   Encounter Dialog (citation deep-links only)
   ═══════════════════════════════════════════════ */

function openEncounterDialog(patient, highlight) {
  if (typeof highlight === "string") highlight = { date: highlight };

  if (highlight && (highlight.section || highlight.preview)) {
    state.revealedIds.add(patient.id);
  }

  const revealed = state.revealAll || state.revealedIds.has(patient.id);
  const masked = !revealed;

  for (const mark of els.encounterDialog.querySelectorAll("mark.cite-highlight")) mark.replaceWith(mark.textContent);
  for (const el of els.encounterDialog.querySelectorAll(".highlight-section")) el.classList.remove("highlight-section");
  for (const el of els.encounterDialog.querySelectorAll(".highlighted")) el.classList.remove("highlighted");

  els.dialogPatientName.textContent = patient.name || "Patient";
  els.dialogPatientMeta.textContent = `${patient.sex_gender || "Unknown"} · ${patient.ethnicity || "Unknown"} · ${patient.encounter_count || 0} encounters`;
  els.dialogProblemList.textContent = toText(patient.sections?.problem_list);
  els.dialogAllergies.textContent = maskText(toText(patient.sections?.allergies), masked);
  els.dialogMeds.textContent = maskText(toText(patient.sections?.medications), masked);
  els.dialogAllergies.classList.toggle("masked", masked);
  els.dialogMeds.classList.toggle("masked", masked);

  const encounters = (patient.encounters || []).slice().sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  els.dialogEncounterList.innerHTML = encounters.map((enc) => renderEncounterItem(enc, masked)).join("");

  if (typeof els.encounterDialog.showModal === "function") els.encounterDialog.showModal();
  else els.encounterDialog.setAttribute("open", "open");

  if (highlight) setTimeout(() => applyDialogHighlight(highlight), 150);
}

function applyDialogHighlight(hl) {
  const { date, section, preview, query } = hl;

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

  if (!date) return;
  const item = [...els.dialogEncounterList.querySelectorAll(".encounter-item")].find((el) => el.dataset.date === date);
  if (!item) return;

  item.classList.add("highlighted");
  const details = item.querySelector("details");
  if (details) details.open = true;

  const textFound = tryHighlightText(item, query, preview);

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

  const scrollTarget = item.querySelector(".cite-highlight") || item.querySelector(".highlight-section") || item;
  setTimeout(() => scrollTarget.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
}

function tryHighlightText(container, query, preview) {
  if (!container || (!query && !preview)) return false;

  const candidates = [];
  if (query) {
    const q = query.trim();
    candidates.push(q);
    const words = q.split(/\s+/).filter((w) => w.length >= 4);
    if (words.length > 2) {
      for (let len = Math.min(words.length, 3); len >= 2; len--) {
        for (let i = 0; i <= words.length - len; i++) candidates.push(words.slice(i, i + len).join(" "));
      }
    }
  }
  if (preview) {
    const raw = preview.trim().replace(/^…+/, "").replace(/…+$/, "").trim();
    const phrases = raw.split(/[.;,\n]+/).map((p) => p.trim()).filter((p) => p.length >= 8);
    phrases.sort((a, b) => b.length - a.length);
    candidates.push(...phrases.slice(0, 4));
  }

  const seen = new Set();
  const unique = candidates.filter((c) => { if (!c || c.length < 4) return false; const k = c.toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; });

  for (const candidate of unique) {
    const search = candidate.toLowerCase();
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.parentElement.closest("summary, strong")) continue;
      const idx = node.textContent.toLowerCase().indexOf(search);
      if (idx < 0) continue;
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


/* ═══════════════════════════════════════════════
   Filters & Refresh
   ═══════════════════════════════════════════════ */

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

function currentParams() {
  return new URLSearchParams({
    q: els.q.value.trim(),
    city: els.city.value, province: els.province.value,
    sex_gender: els.sexGender.value, ethnicity: els.ethnicity.value,
    known_allergy: els.knownAllergy.value,
    organization: els.organization.value, practitioner: els.practitioner.value,
    encounter_type: els.encounterType.value, setting: els.setting.value,
    min_age: els.minAge.value, max_age: els.maxAge.value,
    date_from: els.dateFrom.value, date_to: els.dateTo.value,
  });
}

async function fetchFilteredPatients() {
  const resp = await fetch(`/api/patients?${currentParams()}`);
  const payload = await resp.json();
  state.filtered = payload.results || [];
}

let refreshTimer = null;
function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(async () => {
    await fetchFilteredPatients();
    renderPatientList();
    updateFilterBadges();
  }, 140);
}

/* ── Elasticsearch keyword search (@prefix) ── */

function hideEsDropdown() {
  if (els.esDropdown) {
    els.esDropdown.classList.remove("visible");
    els.esDropdown.innerHTML = "";
  }
}

function showEsDropdown(content) {
  if (!els.esDropdown) return;
  els.esDropdown.innerHTML = content;
  els.esDropdown.classList.add("visible");
}

function renderEsResults(data) {
  hideEsDropdown();

  if (data.error === "es_unavailable") {
    els.resultMeta.textContent = "Elasticsearch unavailable";
    state.filtered = [];
    renderPatientList();
    return;
  }

  if (data.multi_bucket) {
    const matchedNames = new Set(data.results.map(r => r.full_name));
    state.filtered = state.data.filter(p => matchedNames.has(p.name));
    renderPatientList();
    return;
  }

  if (!data.results || data.results.length === 0) {
    state.filtered = [];
    renderPatientList();
    return;
  }

  const bucketLabel = {
    first_name: "First Name",
    last_name: "Last Name",
    health_number: "Health Number"
  }[data.bucket] || data.bucket;

  const matchedNames = new Set(data.results.map(r => r.full_name));
  state.filtered = state.data.filter(p => matchedNames.has(p.name));

  for (const patient of state.filtered) {
    const match = data.results.find(r => r.full_name === patient.name);
    if (match) {
      patient.matched_fields = [bucketLabel];
    }
  }

  renderPatientList();
}

async function performEsSearch(query) {
  if (state.esSearchInFlight) return;

  state.esSearchInFlight = true;
  try {
    const resp = await fetch(`/api/es/search?q=${encodeURIComponent(query)}`);
    const data = await resp.json();
    renderEsResults(data);
  } catch (err) {
    showEsDropdown('<div class="es-item es-error">Search error</div>');
  } finally {
    state.esSearchInFlight = false;
  }
}

function handleSearchInput() {
  const value = els.q.value;

  if (value.startsWith("@")) {
    const query = value.slice(1);
    clearTimeout(refreshTimer);

    if (query.length < 2) {
      hideEsDropdown();
      state.filtered = state.data;
      for (const p of state.filtered) { delete p.matched_fields; }
      renderPatientList();
      return;
    }

    clearTimeout(state.esDebounceTimer);
    state.esDebounceTimer = setTimeout(() => {
      if (!state.esSearchInFlight) performEsSearch(query);
    }, 500);
  } else {
    hideEsDropdown();
    clearTimeout(state.esDebounceTimer);
    for (const p of state.data) { delete p.matched_fields; }
    scheduleRefresh();
  }
}

document.addEventListener("click", (e) => {
  if (els.esDropdown && !els.esDropdown.contains(e.target) && e.target !== els.q) {
    hideEsDropdown();
  }
});

function clearAllFilters() {
  for (const el of inputs) {
    if (el.tagName === "SELECT") { el.selectedIndex = 0; continue; }
    el.value = "";
  }
  els.knownAllergy.value = "all";
  scheduleRefresh();
}

function updateFilterBadges() {
  const badges = [];
  if (els.city.value) badges.push(els.city.value);
  if (els.province.value) badges.push(els.province.value);
  if (els.sexGender.value) badges.push(els.sexGender.value);
  if (els.ethnicity.value) badges.push(els.ethnicity.value);
  if (els.knownAllergy.value !== "all") badges.push(`Allergy: ${els.knownAllergy.value}`);
  if (els.organization.value) badges.push(els.organization.value);
  if (els.practitioner.value) badges.push(els.practitioner.value);
  if (els.encounterType.value) badges.push(els.encounterType.value);
  if (els.setting.value) badges.push(els.setting.value);

  els.activeFilterBadges.innerHTML = badges.map((b) =>
    `<span class="filter-badge">${escapeHtml(b)}</span>`
  ).join("");
}


/* ═══════════════════════════════════════════════
   Boot
   ═══════════════════════════════════════════════ */

async function boot() {
  const [summaryResp, allPatientsResp] = await Promise.all([
    fetch("/api/summary"), fetch("/api/patients"),
  ]);
  const summary = await summaryResp.json();
  const allPatients = await allPatientsResp.json();

  state.summary = summary;
  state.data = allPatients.results || [];
  state.filtered = state.data;

  renderNavStats(summary);
  populateFilters(summary);
  renderPatientList();

  for (const input of inputs) {
    if (!input) continue;
    if (input === els.q) {
      input.addEventListener("input", handleSearchInput);
      input.addEventListener("change", handleSearchInput);
    } else {
      input.addEventListener("input", scheduleRefresh);
      input.addEventListener("change", scheduleRefresh);
    }
  }

  els.toggleAllMask.addEventListener("click", () => {
    state.revealAll = !state.revealAll;
    els.toggleAllMask.setAttribute("aria-pressed", String(state.revealAll));
    els.toggleAllMask.querySelector(".toggle-label").textContent =
      state.revealAll ? "Hide sensitive data" : "Reveal sensitive data";
    if (state.selectedPatient) selectPatient(state.selectedPatient);
  });

  els.clearFilters.addEventListener("click", clearAllFilters);
}

boot().catch((err) => {
  console.error(err);
  els.patientList.innerHTML = `<div class="list-empty">Failed to load: ${err.message}</div>`;
});


/* ═══════════════════════════════════════════════
   Ask AI (Integrated bottom bar)
   ═══════════════════════════════════════════════ */

const chat = {
  bar: document.getElementById("askAiBar"),
  messages: document.getElementById("chatMessages"),
  form: document.getElementById("chatForm"),
  input: document.getElementById("chatInput"),
  mentionList: document.getElementById("chatMentionList"),
  clear: document.getElementById("chatClear"),
  busy: false,
  pendingSources: [],
  mentionState: {
    open: false,
    start: -1,
    query: "",
    options: [],
    activeIndex: 0,
  },
};

function getMentionCandidates() {
  return [...new Set(state.data.map((p) => p.name).filter(Boolean))];
}

function closeMentions() {
  chat.mentionState.open = false;
  chat.mentionState.start = -1;
  chat.mentionState.query = "";
  chat.mentionState.options = [];
  chat.mentionState.activeIndex = 0;
  if (chat.mentionList) {
    chat.mentionList.hidden = true;
    chat.mentionList.innerHTML = "";
  }
}

function applyMention(index) {
  if (!chat.mentionState.open) return;
  const chosen = chat.mentionState.options[index];
  if (!chosen) return;

  const value = chat.input.value;
  const caret = chat.input.selectionStart || value.length;
  const before = value.slice(0, chat.mentionState.start);
  const after = value.slice(caret);
  const insert = `@${chosen} `;
  chat.input.value = `${before}${insert}${after}`;
  const pos = (before + insert).length;
  chat.input.setSelectionRange(pos, pos);
  closeMentions();
}

function renderMentions() {
  if (!chat.mentionList) return;
  if (!chat.mentionState.open || !chat.mentionState.options.length) {
    closeMentions();
    return;
  }

  chat.mentionList.hidden = false;
  chat.mentionList.innerHTML = "";
  chat.mentionState.options.forEach((name, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `chat-mention-item${idx === chat.mentionState.activeIndex ? " active" : ""}`;
    btn.textContent = name;
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      applyMention(idx);
    });
    chat.mentionList.appendChild(btn);
  });
}

function updateMentionsFromInput() {
  const value = chat.input.value;
  const caret = chat.input.selectionStart || value.length;
  const before = value.slice(0, caret);
  const match = before.match(/(^|\s)@([a-zA-Z0-9 .'-]{0,40})$/);
  if (!match) {
    closeMentions();
    return;
  }

  const query = (match[2] || "").trim().toLowerCase();
  const atPos = before.lastIndexOf("@");
  const options = getMentionCandidates()
    .filter((name) => name.toLowerCase().includes(query))
    .slice(0, 8);
  if (!options.length) {
    closeMentions();
    return;
  }

  chat.mentionState.open = true;
  chat.mentionState.start = atPos;
  chat.mentionState.query = query;
  chat.mentionState.options = options;
  chat.mentionState.activeIndex = 0;
  renderMentions();
}

function addBubble(cls, html) {
  const div = document.createElement("div");
  div.className = `chat-bubble ${cls}`;
  div.innerHTML = html;
  chat.messages.appendChild(div);
  chat.bar.classList.add("has-messages");
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
  el.innerHTML = `<div class="chat-typing-orb"></div><span class="chat-typing-text">Thinking</span>`;
  chat.messages.appendChild(el);
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("chatTyping");
  if (el) el.remove();
}

function clearChat() {
  chat.pendingSources = [];
  closeMentions();
  chat.bar.classList.remove("has-messages");
  chat.messages.innerHTML = `
    <div class="chat-welcome">
      <p>Ask about patient records, conditions, or metrics.</p>
      <p class="chat-welcome-hint">Try: "Which patients have diabetes?" or "Chart A1C for Eleanor Voss"</p>
    </div>`;
}

/* ── Thinking Container ── */

function getOrCreateThinking() {
  let container = chat.messages.querySelector(".thinking-container:last-of-type");
  if (container && !container.dataset.done) return container;

  container = document.createElement("div");
  container.className = "thinking-container expanded";
  container.innerHTML = `
    <div class="thinking-header">
      <div class="thinking-orb active"></div>
      <div class="thinking-label"><span class="thinking-text">Working</span></div>
      <svg class="thinking-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="thinking-steps"></div>
  `;
  container.querySelector(".thinking-header").addEventListener("click", () => container.classList.toggle("expanded"));
  chat.messages.appendChild(container);
  chat.bar.classList.add("has-messages");
  chat.messages.scrollTop = chat.messages.scrollHeight;
  return container;
}

function addThinkingStep(type, text) {
  const container = getOrCreateThinking();
  const steps = container.querySelector(".thinking-steps");
  const step = document.createElement("div");
  step.className = `thinking-step ${type}`;
  step.innerHTML = `<span class="thinking-step-icon"></span><span class="thinking-step-text">${escapeHtml(text)}</span>`;
  steps.appendChild(step);
  const label = container.querySelector(".thinking-text");
  if (type === "tool" || type === "search") label.textContent = "Searching";
  else if (type === "chart") label.textContent = "Generating chart";
  else label.textContent = "Working";
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function finalizeThinking() {
  const container = chat.messages.querySelector(".thinking-container:not([data-done])");
  if (!container) return;
  container.dataset.done = "true";
  container.classList.remove("expanded");
  const orb = container.querySelector(".thinking-orb");
  if (orb) orb.classList.remove("active");
  const label = container.querySelector(".thinking-text");
  const count = container.querySelectorAll(".thinking-step").length;
  if (label) label.textContent = count > 0 ? `${count} step${count > 1 ? "s" : ""} completed` : "Done";
}

/* ── Action Buttons ── */

function makeActionBtn(svg, labelText, onClick) {
  const btn = document.createElement("button");
  btn.className = "chat-action-btn";
  btn.type = "button";
  btn.innerHTML = svg + (labelText ? `<span class="btn-label">${labelText}</span>` : "");
  btn.addEventListener("click", onClick);
  return btn;
}

function createActionButtons(bubble) {
  const bar = document.createElement("div");
  bar.className = "chat-actions";

  const copyBtn = makeActionBtn(
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
    "Copy",
    () => {
      navigator.clipboard.writeText(bubble.textContent || bubble.innerText).then(() => {
        copyBtn.querySelector(".btn-label").textContent = "Copied!";
        copyBtn.classList.add("active");
        setTimeout(() => { copyBtn.querySelector(".btn-label").textContent = "Copy"; copyBtn.classList.remove("active"); }, 1500);
      });
    }
  );
  bar.appendChild(copyBtn);

  const upBtn = makeActionBtn(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>`, null, () => { upBtn.classList.toggle("active"); downBtn.classList.remove("active"); });
  upBtn.title = "Helpful";
  bar.appendChild(upBtn);

  const downBtn = makeActionBtn(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/><path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>`, null, () => { downBtn.classList.toggle("active"); upBtn.classList.remove("active"); });
  downBtn.title = "Not helpful";
  bar.appendChild(downBtn);

  return bar;
}

/* ── Send & SSE ── */

async function sendMessage(text) {
  if (chat.busy || !text.trim()) return;
  chat.busy = true;
  chat.form.querySelector("button[type=submit]").disabled = true;

  const welcome = chat.messages.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  addBubble("user", escapeHtml(text));
  chat.bar.classList.add("has-messages", "expanded");
  showTyping();

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (!resp.ok) { hideTyping(); addBubble("error", `Server error (${resp.status})`); return; }

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
        if (line.startsWith("event: ")) eventType = line.slice(7).trim();
        else if (line.startsWith("data: ") && eventType) {
          try { handleSSE(eventType, JSON.parse(line.slice(6))); } catch {}
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
    chat.form.querySelector("button[type=submit]").disabled = false;
    chat.input.focus();
  }
}

function handleSSE(type, data) {
  switch (type) {
    case "status":
      hideTyping(); addThinkingStep("status", data.text || "Processing..."); showTyping(); break;
    case "tool_call": {
      hideTyping();
      const stepType = data.tool === "chart" ? "chart" : "search";
      const label = data.tool === "chart" ? `Chart: ${data.patient} — ${data.metric}` : `Search: ${data.query || data.keyword || ""}`;
      addThinkingStep(stepType, label); showTyping(); break;
    }
    case "sources":
      chat.pendingSources = chat.pendingSources.concat(data.sources || []); break;
    case "chart":
      hideTyping(); addChart(data.b64, `${data.metric} — ${data.patient}`); showTyping(); break;
    case "reply": {
      hideTyping(); finalizeThinking();
      const sources = chat.pendingSources;
      const group = document.createElement("div");
      group.className = "chat-response-group";
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble assistant";
      bubble.innerHTML = formatReply(data.text || "", sources);
      group.appendChild(bubble);
      group.appendChild(createActionButtons(bubble));
      chat.messages.appendChild(group);
      attachCitationClicks(bubble, sources);
      linkPatientNames(bubble);
      if (sources.length) appendSourceCards(sources);
      chat.pendingSources = [];
      chat.messages.scrollTop = chat.messages.scrollHeight;
      break;
    }
    case "open_timeline": {
      const p = state.data.find((pt) => pt.name.toLowerCase() === (data.patient_name || "").toLowerCase());
      if (p) selectPatient(p);
      break;
    }
    case "error": hideTyping(); addBubble("error", escapeHtml(data.text || "Unknown error")); break;
    case "done": hideTyping(); finalizeThinking(); break;
  }
}

function formatReply(text, sources) {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/(?:^|\n)((?:[-*] .+(?:\n|$))+)/g, (block) => {
    const items = block.trim().split("\n").map((l) => `<li>${l.replace(/^[-*]\s+/, "")}</li>`).join("");
    return `<ul>${items}</ul>`;
  });
  html = html.replace(/(?:^|\n)((?:\d+\.\s+.+(?:\n|$))+)/g, (block) => {
    const items = block.trim().split("\n").map((l) => `<li>${l.replace(/^\d+\.\s+/, "")}</li>`).join("");
    return `<ol>${items}</ol>`;
  });
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  html = `<p>${html}</p>`;
  html = html.replace(/<p>\s*<\/p>/g, "");
  html = html.replace(/<p>(<[uo]l>)/g, "$1");
  html = html.replace(/(<\/[uo]l>)<\/p>/g, "$1");

  if (sources && sources.length) {
    html = html.replace(/\[(\d+)\]/g, (match, num) => {
      const idx = parseInt(num) - 1;
      if (idx >= 0 && idx < sources.length) {
        const src = sources[idx];
        return `<button class="citation-ref" data-src-idx="${idx}" title="${escapeHtml(src.patient_name + " · " + src.section)}"><span class="ref-num">${num}</span> ${escapeHtml(src.patient_name || "Source")}</button>`;
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
      if (src) openTimelineFromChat(src.patient_name, { date: src.encounter_date, section: src.section, preview: src.preview, query: src.query });
    });
  });
}

function appendSourceCards(sources) {
  const wrapper = document.createElement("div");
  wrapper.className = "chat-sources";

  const seen = new Set();
  const unique = [];
  for (const src of sources) {
    const key = `${src.patient_name}|${src.encounter_date || ""}|${src.section}`;
    if (seen.has(key)) continue; seen.add(key); unique.push(src);
  }

  const header = document.createElement("div");
  header.className = "sources-header";
  header.innerHTML = `<span class="sources-header-label">Sources</span><span class="sources-count">${unique.length}</span><svg class="sources-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>`;
  header.addEventListener("click", () => wrapper.classList.toggle("expanded"));
  wrapper.appendChild(header);

  const list = document.createElement("div");
  list.className = "sources-list";
  for (const src of unique) {
    const card = document.createElement("div");
    card.className = "source-card";
    card.innerHTML = `
      <span class="source-num">${src.index}</span>
      <div class="source-info">
        <div class="source-title">${escapeHtml(src.patient_name || "Source")}</div>
        <div class="source-meta">${escapeHtml([src.section, src.encounter_date].filter(Boolean).join(" · "))}</div>
        ${src.preview ? `<div class="source-excerpt">${escapeHtml(src.preview)}</div>` : ""}
      </div>
      <span class="source-arrow">\u2197</span>
    `;
    card.addEventListener("click", () => openTimelineFromChat(src.patient_name, { date: src.encounter_date, section: src.section, preview: src.preview, query: src.query }));
    list.appendChild(card);
  }
  wrapper.appendChild(list);
  chat.messages.appendChild(wrapper);
  chat.messages.scrollTop = chat.messages.scrollHeight;
}

function linkPatientNames(bubble) {
  const names = state.data.map((p) => p.name).filter(Boolean);
  if (!names.length) return;
  const walker = document.createTreeWalker(bubble, NodeFilter.SHOW_TEXT);
  const replacements = [];
  while (walker.nextNode()) {
    const tn = walker.currentNode;
    if (tn.parentElement.closest("button, a, .citation-ref")) continue;
    for (const name of names) { if (tn.textContent.includes(name)) replacements.push({ textNode: tn, name }); }
  }
  for (const { textNode, name } of replacements) {
    const parts = textNode.textContent.split(name);
    const frag = document.createDocumentFragment();
    parts.forEach((part, i) => {
      if (i > 0) {
        const btn = document.createElement("button");
        btn.className = "patient-link";
        btn.textContent = name;
        btn.title = `Select ${name}`;
        btn.addEventListener("click", () => {
          const p = state.data.find((pt) => pt.name === name);
          if (p) selectPatient(p);
        });
        frag.appendChild(btn);
      }
      if (part) frag.appendChild(document.createTextNode(part));
    });
    textNode.parentNode.replaceChild(frag, textNode);
  }
}

function normalizePatientKey(raw) {
  return String(raw || "")
    .toLowerCase()
    .replace(/^@+/, "")
    .replace(/[^a-z0-9\s'-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function openTimelineFromChat(patientName, highlight) {
  const nameKey = normalizePatientKey(patientName);
  const patient = state.data.find((p) => normalizePatientKey(p.name) === nameKey)
    || state.data.find((p) => normalizePatientKey(p.name).includes(nameKey) || nameKey.includes(normalizePatientKey(p.name)));
  if (!patient) { addBubble("error", `Patient "${escapeHtml(patientName)}" not found.`); return; }

  // Auto-reveal sensitive data when navigating from citation
  if (highlight && (highlight.section || highlight.preview)) {
    state.revealedIds.add(patient.id);
  }

  selectPatient(patient);

  if (highlight && (highlight.date || highlight.section)) {
    setTimeout(() => applyDetailHighlight(highlight), 120);
  }
}

function applyDetailHighlight(hl) {
  const { date, section, preview, query } = hl;

  // Clear any previous highlights in the detail panel
  for (const mark of els.detailEncounterList.querySelectorAll("mark.cite-highlight")) mark.replaceWith(mark.textContent);
  for (const el of els.detailEncounterList.querySelectorAll(".highlight-section")) el.classList.remove("highlight-section");
  for (const el of els.detailEncounterList.querySelectorAll(".highlighted")) el.classList.remove("highlighted");
  // Also clear highlights in the summary area
  const summaryEl = document.getElementById("detailSummary");
  if (summaryEl) {
    for (const mark of summaryEl.querySelectorAll("mark.cite-highlight")) mark.replaceWith(mark.textContent);
    for (const el of summaryEl.querySelectorAll(".highlight-section")) el.classList.remove("highlight-section");
  }

  // If no date, try to highlight a top-level section (problem list, allergies, meds)
  if (!date && section) {
    const sectionMap = {
      "problem list": els.detailProblems,
      "allergies": els.detailAllergies,
      "medications": els.detailMeds,
      "medication summary": els.detailMeds,
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

  if (!date) return;

  // Find the matching encounter item in the detail panel
  const item = [...els.detailEncounterList.querySelectorAll(".encounter-item")].find((el) => el.dataset.date === date);
  if (!item) return;

  item.classList.add("highlighted");
  const details = item.querySelector("details");
  if (details) details.open = true;

  const textFound = tryHighlightText(item, query, preview);

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

  const scrollTarget = item.querySelector(".cite-highlight") || item.querySelector(".highlight-section") || item;
  setTimeout(() => scrollTarget.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
}

chat.clear.addEventListener("click", clearChat);

// Close encounter dialog when clicking outside the dialog panel
els.encounterDialog.addEventListener("click", (e) => {
  if (!els.encounterDialog.open) return;
  const shell = els.encounterDialog.querySelector(".dialog-shell");
  if (!shell) return;
  const rect = shell.getBoundingClientRect();
  const clickedOutside =
    e.clientX < rect.left || e.clientX > rect.right ||
    e.clientY < rect.top || e.clientY > rect.bottom;
  if (clickedOutside) {
    if (typeof els.encounterDialog.close === "function") els.encounterDialog.close();
    else els.encounterDialog.removeAttribute("open");
  }
});

chat.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chat.input.value.trim();
  if (!text) return;
  closeMentions();
  chat.input.value = "";
  sendMessage(text);
});

chat.input.addEventListener("input", () => {
  updateMentionsFromInput();
});

chat.input.addEventListener("keydown", (e) => {
  if (!chat.mentionState.open) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    chat.mentionState.activeIndex = (chat.mentionState.activeIndex + 1) % chat.mentionState.options.length;
    renderMentions();
    return;
  }
  if (e.key === "ArrowUp") {
    e.preventDefault();
    chat.mentionState.activeIndex =
      (chat.mentionState.activeIndex - 1 + chat.mentionState.options.length) % chat.mentionState.options.length;
    renderMentions();
    return;
  }
  if (e.key === "Enter" || e.key === "Tab") {
    e.preventDefault();
    applyMention(chat.mentionState.activeIndex);
    return;
  }
  if (e.key === "Escape") {
    e.preventDefault();
    closeMentions();
  }
});

chat.input.addEventListener("blur", () => {
  setTimeout(() => closeMentions(), 120);
});

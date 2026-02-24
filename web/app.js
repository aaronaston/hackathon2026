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
    <article class="encounter-item">
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

function openEncounterDialog(patient) {
  const revealed = state.revealAll || state.revealedIds.has(patient.id);
  const masked = !revealed;

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

const state = {
  data: [],
  filtered: [],
  revealAll: false,
  revealedIds: new Set(),
};

const els = {
  stats: document.getElementById("stats"),
  results: document.getElementById("results"),
  toggleAllMask: document.getElementById("toggleAllMask"),
  q: document.getElementById("q"),
  city: document.getElementById("city"),
  sexGender: document.getElementById("sex_gender"),
  ethnicity: document.getElementById("ethnicity"),
  knownAllergy: document.getElementById("known_allergy"),
  minAge: document.getElementById("min_age"),
  maxAge: document.getElementById("max_age"),
  cardTemplate: document.getElementById("card-template"),
};

function createOption(value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = value;
  return option;
}

function renderStats(summary) {
  const cards = [
    ["Total Patients", summary.total_patients],
    ["Known Allergies", summary.known_allergy_count],
    ["Cities", Object.keys(summary.city_counts).length],
    ["Sex/Gender Tags", Object.keys(summary.sex_gender_counts).length],
  ];

  els.stats.innerHTML = "";
  for (const [k, v] of cards) {
    const div = document.createElement("div");
    div.className = "stat";
    div.innerHTML = `<p class="k">${k}</p><p class="v">${v}</p>`;
    els.stats.appendChild(div);
  }
}

function populateFilters(data) {
  const cities = [...new Set(data.map((x) => x.location.city).filter(Boolean))].sort();
  const sexes = [...new Set(data.map((x) => x.sex_gender).filter(Boolean))].sort();
  const ethnicities = [...new Set(data.map((x) => x.ethnicity).filter(Boolean))].sort();

  for (const c of cities) els.city.appendChild(createOption(c));
  for (const s of sexes) els.sexGender.appendChild(createOption(s));
  for (const e of ethnicities) els.ethnicity.appendChild(createOption(e));
}

function maskText(value, isMasked) {
  if (!value) return "-";
  if (!isMasked) return value;
  return value.replace(/[A-Za-z0-9]/g, "*");
}

function applyMaskClasses(container, masked) {
  const sensitiveEls = container.querySelectorAll(".sensitive");
  for (const el of sensitiveEls) {
    el.classList.toggle("masked", masked);
  }
}

function toText(list) {
  if (!Array.isArray(list) || list.length === 0) return "-";
  return list.join(" ");
}

function cardForPatient(p) {
  const frag = els.cardTemplate.content.cloneNode(true);
  const eyeBtn = frag.querySelector(".eye-btn");

  const isRevealed = state.revealAll || state.revealedIds.has(p.id);
  const isMasked = !isRevealed;

  frag.querySelector(".name").textContent = p.name;
  frag.querySelector(".meta").textContent = `${p.sex_gender} | ${p.ethnicity}`;

  const scoreEl = frag.querySelector(".score");
  scoreEl.textContent = p.search_score ? `Relevance ${p.search_score}` : "";

  const chips = frag.querySelector(".chips");
  const chipParts = [
    `${p.age ?? "?"} y`,
    `${p.location.city || "Unknown"}, ${p.location.province || ""}`.trim(),
    p.known_allergy ? "Known allergy" : "No known allergy",
  ];
  for (const text of chipParts) {
    const c = document.createElement("span");
    c.className = "chip";
    if (text.includes("Known allergy")) c.classList.add("warn");
    if (text.includes("No known allergy")) c.classList.add("ok");
    c.textContent = text;
    chips.appendChild(c);
  }

  if (Array.isArray(p.matched_fields) && p.matched_fields.length) {
    const c = document.createElement("span");
    c.className = "chip";
    c.textContent = `Matched: ${p.matched_fields.join(", ")}`;
    chips.appendChild(c);
  }

  frag.querySelector(".dob").textContent = maskText(p.date_of_birth, isMasked);
  frag.querySelector(".address").textContent = maskText(p.address, isMasked);
  frag.querySelector(".allergies").textContent = maskText(toText(p.sections.allergies), isMasked);
  frag.querySelector(".meds").textContent = maskText(toText(p.sections.medications), isMasked);
  frag.querySelector(".problem-list").textContent = toText(p.sections.problem_list);
  frag.querySelector(".diagnostics").textContent = maskText(toText(p.sections.diagnostic_results), isMasked);
  frag.querySelector(".social").textContent = maskText(toText(p.sections.social_history), isMasked);
  frag.querySelector(".plan").textContent = toText(p.sections.plan_of_care);

  applyMaskClasses(frag, isMasked);
  eyeBtn.setAttribute("aria-pressed", String(isRevealed));

  eyeBtn.addEventListener("click", () => {
    if (state.revealedIds.has(p.id)) {
      state.revealedIds.delete(p.id);
    } else {
      state.revealedIds.add(p.id);
    }
    renderResults();
  });

  return frag;
}

function inAgeRange(p) {
  const min = Number(els.minAge.value);
  const max = Number(els.maxAge.value);

  if (Number.isFinite(min) && els.minAge.value !== "" && (p.age == null || p.age < min)) return false;
  if (Number.isFinite(max) && els.maxAge.value !== "" && (p.age == null || p.age > max)) return false;
  return true;
}

async function fetchPatients() {
  const params = new URLSearchParams({
    q: els.q.value.trim(),
    city: els.city.value,
    sex_gender: els.sexGender.value,
    ethnicity: els.ethnicity.value,
    known_allergy: els.knownAllergy.value,
  });

  const resp = await fetch(`/api/patients?${params.toString()}`);
  const payload = await resp.json();
  state.filtered = payload.results.filter(inAgeRange);
}

function renderResults() {
  els.results.innerHTML = "";

  if (state.filtered.length === 0) {
    const p = document.createElement("p");
    p.className = "panel empty";
    p.textContent = "No patients match this filter set.";
    els.results.appendChild(p);
    return;
  }

  for (const patient of state.filtered) {
    els.results.appendChild(cardForPatient(patient));
  }
}

let timer = null;
function scheduleRefresh() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(async () => {
    await fetchPatients();
    renderResults();
  }, 140);
}

async function boot() {
  const [summaryResp, dataResp] = await Promise.all([
    fetch("/api/summary"),
    fetch("/api/patients"),
  ]);
  const summary = await summaryResp.json();
  const dataPayload = await dataResp.json();

  state.data = dataPayload.results;
  state.filtered = dataPayload.results;

  renderStats(summary);
  populateFilters(state.data);
  renderResults();

  [els.q, els.city, els.sexGender, els.ethnicity, els.knownAllergy, els.minAge, els.maxAge].forEach((el) => {
    el.addEventListener("input", scheduleRefresh);
    el.addEventListener("change", scheduleRefresh);
  });

  els.toggleAllMask.addEventListener("click", () => {
    state.revealAll = !state.revealAll;
    els.toggleAllMask.setAttribute("aria-pressed", String(state.revealAll));
    els.toggleAllMask.querySelector(".toggle-label").textContent = state.revealAll ? "Hide All" : "Reveal All";
    renderResults();
  });
}

boot().catch((err) => {
  console.error(err);
  els.results.innerHTML = `<p class="panel empty">Failed to load data: ${err.message}</p>`;
});

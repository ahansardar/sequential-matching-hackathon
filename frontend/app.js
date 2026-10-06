const state = {
  data: null,
  pool: 'public_01',
  outputPool: 'public_05',
  visibleMembers: 50,
};

const el = id => document.getElementById(id);
const fmt = (value, digits = 3) => value === null || value === undefined ? '—' : Number(value).toFixed(digits);
const pct = value => value === null || value === undefined ? '—' : `${Math.round(Number(value) * 100)}%`;
const text = value => String(value ?? '').replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
const shortId = id => String(id).replace('syn_', '');
const emptyRow = (columns, message) => `<tr><td colspan="${columns}" class="empty">${message}</td></tr>`;

async function load() {
  try {
    const response = await fetch('data/dashboard.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    setup();
    renderAll();
  } catch (error) {
    document.querySelector('main').innerHTML = `<section class="card"><div class="empty"><h1>Dashboard data is missing</h1><p>Run <code>python frontend/build_dashboard_data.py</code> from the repository folder, then reload.</p><p>${error.message}</p></div></section>`;
  }
}

function setup() {
  document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
  const poolOptions = state.data.pools.map(pool => `<option value="${pool.id}">${pool.id}</option>`).join('');
  el('pool-select').innerHTML = poolOptions;
  el('output-pool').innerHTML = poolOptions;
  el('pool-select').value = state.pool;
  el('output-pool').value = state.outputPool;
  el('pool-select').addEventListener('change', event => { state.pool = event.target.value; state.visibleMembers = 50; renderDataset(); });
  el('output-pool').addEventListener('change', event => { state.outputPool = event.target.value; renderOutput(); });
  el('member-search').addEventListener('input', () => { state.visibleMembers = 50; renderMembers(); });
  el('availability-filter').addEventListener('change', () => { state.visibleMembers = 50; renderMembers(); });
  el('show-more-members').addEventListener('click', () => { state.visibleMembers += 50; renderMembers(); });
  el('drawer-close').addEventListener('click', closeDrawer);
  el('drawer-scrim').addEventListener('click', closeDrawer);
  el('run-select').addEventListener('change', renderRunDetails);
}

function showView(view) {
  document.querySelectorAll('.view').forEach(node => node.classList.toggle('active', node.id === `view-${view}`));
  document.querySelectorAll('.tab').forEach(node => node.classList.toggle('active', node.dataset.view === view));
  window.scrollTo(0, 0);
}

function summaryItem(label, value, note = '') {
  return `<div class="summary-item"><span>${label}</span><strong>${value}</strong>${note ? `<small>${note}</small>` : ''}</div>`;
}

function renderAll() {
  renderOverview();
  renderDataset();
  renderOutput();
  renderRuns();
}

function renderOverview() {
  const members = state.data.pools.reduce((sum, pool) => sum + pool.members, 0);
  const introductions = state.data.pools.reduce((sum, pool) => sum + pool.introductions, 0);
  const feedback = state.data.pools.reduce((sum, pool) => sum + pool.feedback, 0);
  const episodes = Math.max(0, ...state.data.experiments.map(run => run.episodes || 0));
  el('overview-summary').innerHTML = [
    summaryItem('Synthetic members', members.toLocaleString(), `${state.data.pools.length} disjoint pools`),
    summaryItem('Historical introductions', introductions.toLocaleString(), 'Visible in public snapshots'),
    summaryItem('Feedback events', feedback.toLocaleString(), 'Visible before new decisions'),
    summaryItem('Episodes per saved run', episodes, `${state.data.scenarios.length} public scenarios`),
  ].join('');

  el('pool-overview-rows').innerHTML = state.data.pools.map(pool => `<tr>
    <td class="mono">${pool.id}</td><td>${pool.members}</td><td>${pool.available}</td><td>${pool.introductions}</td><td>${pool.feedback}</td><td>${pct(pool.hardObservedRate)}</td><td>${pct(pool.softObservedRate)}</td>
  </tr>`).join('');

  const runs = [...state.data.experiments].sort((a, b) => (b.primary ?? -1) - (a.primary ?? -1));
  el('overview-run-rows').innerHTML = runs.map(run => `<tr>
    <td>${run.label}<br><span class="muted mono">${run.source}</span></td><td>${fmt(run.primary)}</td><td>${pct(run.overall.coverage)}</td><td>${fmt(run.overall.mutual_acceptances_per_100, 2)}</td><td>${fmt(run.overall.ask_cost, 1)}</td><td>${run.episodes}</td><td class="${run.valid ? 'yes' : 'no'}">${run.valid ? 'Yes' : 'No'}</td>
  </tr>`).join('') || emptyRow(7, 'No saved evaluation results found.');
}

function renderDataset() {
  const pool = state.data.pools.find(item => item.id === state.pool);
  el('dataset-summary').innerHTML = [
    summaryItem('Snapshot day', pool.day),
    summaryItem('Members', pool.members),
    summaryItem('Available', pool.available),
    summaryItem('Hard fields known', pct(pool.hardObservedRate)),
    summaryItem('Soft fields known', pct(pool.softObservedRate)),
  ].join('');
  renderMembers();
}

function filteredMembers() {
  const query = el('member-search').value.trim().toLowerCase();
  const availability = el('availability-filter').value;
  return state.data.poolDetails[state.pool].members.filter(member => {
    const searchable = [member.id, member.zone, member.gender].join(' ').toLowerCase();
    const matchesAvailability = availability === 'all' || (availability === 'available' ? member.available : !member.available);
    return (!query || searchable.includes(query)) && matchesAvailability;
  });
}

function renderMembers() {
  const members = filteredMembers();
  const shown = members.slice(0, state.visibleMembers);
  el('member-count').textContent = `Showing ${shown.length} of ${members.length}`;
  el('member-rows').innerHTML = shown.map(member => `<tr class="clickable" data-member="${member.id}">
    <td class="mono">${shortId(member.id)}</td><td>${member.age}</td><td>${text(member.gender)}</td><td>${member.zone}</td><td>${member.arrivalDay}</td><td class="${member.available ? 'yes' : 'muted'}">${member.available ? 'Yes' : 'No'}</td><td>${member.hardKnown} / ${member.hardTotal}</td><td>${member.softKnown} / ${member.softTotal}</td>
  </tr>`).join('') || emptyRow(8, 'No members match the current filters.');
  el('show-more-members').hidden = shown.length >= members.length;
  document.querySelectorAll('[data-member]').forEach(row => row.addEventListener('click', () => openMember(row.dataset.member)));
}

function openMember(memberId) {
  const member = state.data.poolDetails[state.pool].members.find(item => item.id === memberId);
  const fieldRows = fieldNames => fieldNames.map(field => {
    const raw = member.fields[field];
    const value = raw === null || raw === undefined ? 'Unknown' : Array.isArray(raw) ? raw.map(text).join(', ') : typeof raw === 'boolean' ? (raw ? 'Yes' : 'No') : text(raw);
    return `<div class="field-row"><strong>${text(field)}</strong><span>${value}</span><span>${text(member.statuses[field] || 'unknown')}</span></div>`;
  }).join('');
  el('drawer-content').innerHTML = `<h2 class="member-title mono">${shortId(member.id)}</h2><p class="member-meta">Age ${member.age} · ${text(member.gender)} · ${member.zone} · arrived day ${member.arrivalDay} · ${member.available ? 'available' : 'unavailable'}</p>
    <section class="field-section"><h3>Hard constraint fields</h3>${fieldRows(['age_min','age_max','who_to_meet','relationship_structure','smoking','partner_smoking','has_children','partner_children','wants_children','acceptable_zones','schedule'])}</section>
    <section class="field-section"><h3>Soft preference fields</h3>${fieldRows(['relationship_goal','relationship_pace','lifestyle','conversations','emotional_availability','space_for_relationship','relocate'])}</section>`;
  el('member-drawer').classList.add('open');
  el('drawer-scrim').classList.add('open');
  el('member-drawer').setAttribute('aria-hidden', 'false');
}

function closeDrawer() {
  el('member-drawer').classList.remove('open');
  el('drawer-scrim').classList.remove('open');
  el('member-drawer').setAttribute('aria-hidden', 'true');
}

function renderOutput() {
  const output = state.data.poolDetails[state.outputPool];
  el('output-summary').innerHTML = [
    summaryItem('Snapshot day', output.day),
    summaryItem('Ask budget', output.askBudget),
    summaryItem('Clarification requests', output.asks.length),
    summaryItem('Selected matches', output.selectedPairs.length),
    summaryItem('Feasible candidate edges', output.edges.length),
  ].join('');

  el('ask-rows').innerHTML = output.asks.map((ask, index) => `<tr><td>${index + 1}</td><td class="mono">${shortId(ask.member_id)}</td><td>Hard-constraint bundle</td><td>3</td></tr>`).join('') || emptyRow(4, 'No clarification request produced for this snapshot.');
  el('match-rows').innerHTML = output.selectedPairs.map((pair, index) => `<tr><td>${index + 1}</td><td class="mono">${shortId(pair[0])}</td><td class="mono">${shortId(pair[1])}</td><td><span class="tag selected">Selected</span></td></tr>`).join('') || emptyRow(4, 'No match produced for this snapshot.');
  el('edge-rows').innerHTML = output.edges.slice(0, 100).map(edge => `<tr class="${edge.selected ? 'selected' : ''}"><td class="mono">${shortId(edge.left)}</td><td class="mono">${shortId(edge.right)}</td><td>${edge.leftZone}</td><td>${edge.rightZone}</td><td>${fmt(edge.score, 4)}</td><td>${edge.selected ? '<span class="tag selected">Yes</span>' : 'No'}</td></tr>`).join('') || emptyRow(6, 'No reciprocally feasible candidate edge was produced.');
  el('feedback-rows').innerHTML = Object.entries(output.feedbackCounts).map(([event, count]) => `<tr><td>${text(event)}</td><td>${count}</td></tr>`).join('') || emptyRow(2, 'No feedback events are present in this snapshot.');
}

function renderRuns() {
  el('run-select').innerHTML = state.data.experiments.map(run => `<option value="${run.id}">${run.label} — ${run.source}</option>`).join('');
  renderRunDetails();
}

function renderRunDetails() {
  const run = state.data.experiments.find(item => item.id === el('run-select').value) || state.data.experiments[0];
  if (!run) {
    el('run-summary').innerHTML = summaryItem('Saved runs', 0, 'Run an evaluation and rebuild dashboard data.');
    el('scenario-rows').innerHTML = emptyRow(5, 'No saved run found.');
    el('episode-rows').innerHTML = emptyRow(10, 'No saved run found.');
    return;
  }
  el('run-summary').innerHTML = [
    summaryItem('Primary score', fmt(run.primary)),
    summaryItem('Coverage', pct(run.overall.coverage)),
    summaryItem('Mutual / 100', fmt(run.overall.mutual_acceptances_per_100, 2)),
    summaryItem('Ask cost', fmt(run.overall.ask_cost, 1)),
    summaryItem('Valid episodes', run.valid ? `Yes (${run.episodes})` : 'No'),
  ].join('');

  el('scenario-rows').innerHTML = state.data.scenarios.map(scenario => {
    const values = run.scenarios[scenario] || {};
    return `<tr><td>${text(scenario)}</td><td>${fmt(values.msmi_per_100_arrived_members)}</td><td>${pct(values.coverage)}</td><td>${fmt(values.mutual_acceptances_per_100, 2)}</td><td>${fmt(values.ask_cost, 1)}</td></tr>`;
  }).join('');

  const key = run.source.replace('.json', '');
  const episodes = state.data.rawEpisodes?.[key] || [];
  el('episode-rows').innerHTML = episodes.map(row => `<tr><td>${row.seed}</td><td>${text(row.variant)}</td><td class="${row.valid ? 'yes' : 'no'}">${row.valid ? 'Yes' : 'No'}</td><td>${row.assignments}</td><td>${row.mutual_acceptances}</td><td>${row.dates}</td><td>${row.mutual_second_meeting_intention}</td><td>${pct(row.coverage)}</td><td>${row.ask_cost}</td><td>${row.missing_feedback}</td></tr>`).join('') || emptyRow(10, 'This result file has no episode rows.');
}

load();

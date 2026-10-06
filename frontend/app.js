const state = { data: null, view: 'overview', pool: 'public_01', decisionPool: 'public_01', visibleMembers: 50 };
const fmt = (value, digits = 3) => Number(value ?? 0).toFixed(digits);
const pct = value => `${Math.round(Number(value ?? 0) * 100)}%`;
const shortId = id => id.replace('syn_', '').slice(0, 10);
const title = text => text.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const el = id => document.getElementById(id);

async function load() {
  try {
    const response = await fetch('data/dashboard.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    setup();
    renderAll();
  } catch (error) {
    document.querySelector('main').innerHTML = `<article class="panel"><h1>Dashboard data is missing.</h1><p>Run <code>python frontend/build_dashboard_data.py</code>, then reload this page.</p><p>${error.message}</p></article>`;
  }
}

function setup() {
  document.querySelectorAll('.nav-link').forEach(button => button.addEventListener('click', () => showView(button.dataset.view)));
  const options = state.data.pools.map(pool => `<option value="${pool.id}">${pool.id}</option>`).join('');
  el('pool-select').innerHTML = options;
  el('decision-pool').innerHTML = options;
  el('pool-select').addEventListener('change', event => { state.pool = event.target.value; state.visibleMembers = 50; renderDataset(); });
  el('decision-pool').addEventListener('change', event => { state.decisionPool = event.target.value; renderDecisions(); });
  el('member-search').addEventListener('input', () => { state.visibleMembers = 50; renderMembers(); });
  el('availability-filter').addEventListener('change', () => { state.visibleMembers = 50; renderMembers(); });
  el('show-more-members').addEventListener('click', () => { state.visibleMembers += 50; renderMembers(); });
  el('drawer-close').addEventListener('click', closeDrawer);
  el('drawer-scrim').addEventListener('click', closeDrawer);
  el('overview-method').addEventListener('change', renderOverviewMethod);
}

function showView(view) {
  state.view = view;
  document.querySelectorAll('.view').forEach(node => node.classList.toggle('active', node.id === `view-${view}`));
  document.querySelectorAll('.nav-link').forEach(node => node.classList.toggle('active', node.dataset.view === view));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderAll() { renderOverview(); renderDataset(); renderDecisions(); renderExperiments(); }

function renderOverview() {
  const cavia = state.data.experiments.find(method => method.id === 'cavia') || state.data.experiments[0];
  const totalMembers = state.data.pools.reduce((sum, pool) => sum + pool.members, 0);
  const totalIntroductions = state.data.pools.reduce((sum, pool) => sum + pool.introductions, 0);
  el('overview-metrics').innerHTML = [
    ['Synthetic members', totalMembers.toLocaleString(), '10 disjoint public pools'],
    ['Historical introductions', totalIntroductions.toLocaleString(), 'Observable at day 30'],
    ['Public episodes', cavia?.episodes ?? 0, 'Matched seeds and scenarios'],
    ['CAVIA primary score', fmt(cavia?.primary), 'Preliminary—not a leaderboard score'],
  ].map(([label, value, note]) => `<div class="metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join('');
  el('overview-method').innerHTML = state.data.experiments.map(method => `<option value="${method.id}">${method.label}</option>`).join('');
  renderOverviewMethod();
  const greedy = state.data.experiments.find(method => method.id === 'greedy');
  if (cavia && greedy) {
    const delta = cavia.primary - greedy.primary;
    el('current-finding').textContent = `Across ${cavia.episodes} matched public episodes, CAVIA scores ${fmt(cavia.primary)} versus greedy ${fmt(greedy.primary)} (${delta >= 0 ? '+' : ''}${fmt(delta)}). CAVIA helps in several scenarios but loses the sparse-geography success on seed 102.`;
  }
}

function renderOverviewMethod() {
  const method = state.data.experiments.find(item => item.id === el('overview-method').value) || state.data.experiments[0];
  if (!method) return;
  const maxScore = Math.max(1, ...Object.values(method.scenarios).map(row => row.msmi_per_100_arrived_members));
  el('scenario-bars').innerHTML = state.data.scenarios.map(scenario => {
    const value = method.scenarios[scenario]?.msmi_per_100_arrived_members ?? 0;
    return `<div class="bar-row"><span>${title(scenario)}</span><div class="bar-track"><div class="bar-fill" style="width:${value / maxScore * 100}%"></div></div><strong>${fmt(value)}</strong></div>`;
  }).join('');

  const episodes = getExperimentEpisodes(method.source);
  const totals = episodes.reduce((acc, row) => {
    acc.assignments += row.assignments || 0; acc.mutual += row.mutual_acceptances || 0; acc.dates += row.dates || 0; acc.msmi += row.mutual_second_meeting_intention || 0; return acc;
  }, { assignments: 0, mutual: 0, dates: 0, msmi: 0 });
  const max = Math.max(1, totals.assignments);
  el('outcome-funnel').innerHTML = [['Assignments', totals.assignments], ['Mutual yes', totals.mutual], ['Dates', totals.dates], ['MSMI', totals.msmi]].map(([label, value]) => `<div class="funnel-row"><span>${label}</span><div class="funnel-track"><div class="funnel-fill" style="width:${value / max * 100}%"></div></div><strong>${value}</strong></div>`).join('');
}

function getExperimentEpisodes(source) {
  const key = source.replace('.json', '');
  return state.data.rawEpisodes?.[key] || [];
}

function renderDataset() {
  const pool = state.data.pools.find(item => item.id === state.pool);
  el('dataset-summary').innerHTML = [
    ['Snapshot day', pool.day], ['Members', pool.members], ['Available', pool.available], ['Hard fields observed', pct(pool.hardObservedRate)], ['Soft fields observed', pct(pool.softObservedRate)]
  ].map(([label, value]) => `<div class="summary-cell"><small>${label}</small><strong>${value}</strong></div>`).join('');
  renderMembers();
}

function filteredMembers() {
  const detail = state.data.poolDetails[state.pool];
  const query = el('member-search').value.trim().toLowerCase();
  const filter = el('availability-filter').value;
  return detail.members.filter(member => {
    const matchesSearch = !query || [member.id, member.zone, member.gender].some(value => String(value).toLowerCase().includes(query));
    const matchesAvailability = filter === 'all' || (filter === 'available' ? member.available : !member.available);
    return matchesSearch && matchesAvailability;
  });
}

function renderMembers() {
  const members = filteredMembers();
  const shown = members.slice(0, state.visibleMembers);
  el('member-rows').innerHTML = shown.map(member => `<tr class="clickable" data-member="${member.id}"><td class="member-id">${shortId(member.id)}</td><td>${member.age}</td><td>${title(member.gender)}</td><td>${member.zone}</td><td><span class="status-dot ${member.available ? 'yes' : ''}"></span>${member.available ? 'Available' : 'Unavailable'}</td><td><span class="progress-mini"><b style="width:${member.hardKnown / member.hardTotal * 100}%"></b></span>${member.hardKnown}/${member.hardTotal}</td><td><span class="progress-mini"><b style="width:${member.softKnown / member.softTotal * 100}%"></b></span>${member.softKnown}/${member.softTotal}</td></tr>`).join('') || `<tr><td colspan="7" class="empty">No members match these filters.</td></tr>`;
  el('member-count').textContent = `Showing ${Math.min(shown.length, members.length)} of ${members.length}`;
  el('show-more-members').hidden = shown.length >= members.length;
  document.querySelectorAll('[data-member]').forEach(row => row.addEventListener('click', () => openMember(row.dataset.member)));
}

function openMember(id) {
  const member = state.data.poolDetails[state.pool].members.find(item => item.id === id);
  const fieldRows = fields => fields.map(field => {
    const value = member.fields[field];
    const display = value === null || value === undefined ? 'Unknown' : Array.isArray(value) ? value.map(title).join(', ') : typeof value === 'boolean' ? (value ? 'Yes' : 'No') : title(String(value));
    return `<div class="field-row"><strong>${title(field)}</strong><span class="field-value">${display}</span><span>${title(member.statuses[field] || 'unknown')}</span></div>`;
  }).join('');
  el('drawer-content').innerHTML = `<p class="eyebrow">Synthetic member / observable profile</p><h2 class="drawer-title">${shortId(member.id)}</h2><p class="drawer-meta">${member.age} · ${title(member.gender)} · ${member.zone} · arrived day ${member.arrivalDay}</p><div class="field-group"><h3>Hard constraints</h3>${fieldRows(['age_min','age_max','who_to_meet','relationship_structure','smoking','partner_smoking','has_children','partner_children','wants_children','acceptable_zones','schedule'])}</div><div class="field-group"><h3>Soft observations</h3>${fieldRows(['relationship_goal','relationship_pace','lifestyle','conversations','emotional_availability','space_for_relationship','relocate'])}</div>`;
  el('member-drawer').classList.add('open'); el('member-scrim')?.classList.add('open'); el('drawer-scrim').classList.add('open'); el('member-drawer').setAttribute('aria-hidden', 'false');
}

function closeDrawer() { el('member-drawer').classList.remove('open'); el('drawer-scrim').classList.remove('open'); el('member-drawer').setAttribute('aria-hidden', 'true'); }

function renderDecisions() {
  const detail = state.data.poolDetails[state.decisionPool];
  el('decision-day').textContent = `Day ${detail.day} snapshot`;
  el('ask-budget').textContent = `${detail.askBudget} units available`;
  el('pair-count').textContent = `${detail.selectedPairs.length} pairs`;
  el('ask-list').innerHTML = detail.asks.map((ask, index) => `<div class="ask-item"><span class="item-number">${index + 1}</span><div class="item-copy"><strong>${shortId(ask.member_id)}</strong><small>Hard-constraint bundle</small></div><b>3 units</b></div>`).join('') || `<p class="empty">No clarification recommended.</p>`;
  el('pair-list').innerHTML = detail.selectedPairs.slice(0, 12).map((pair, index) => `<div class="pair-item"><span class="item-number">${index + 1}</span><div class="item-copy"><strong>${shortId(pair[0])} ↔ ${shortId(pair[1])}</strong><small>Reciprocally feasible</small></div><b>Selected</b></div>`).join('') || `<p class="empty">No feasible pair selected.</p>`;
  const maxScore = Math.max(1, ...detail.edges.slice(0, 30).map(edge => edge.score));
  el('edge-rows').innerHTML = detail.edges.slice(0, 30).map(edge => `<tr class="${edge.selected ? 'selected-row' : ''}"><td class="member-id">${shortId(edge.left)} ↔ ${shortId(edge.right)}</td><td>${edge.leftZone} / ${edge.rightZone}</td><td><span class="score-bar" style="width:${Math.max(2, edge.score / maxScore * 90)}px"></span>${fmt(edge.score, 2)}</td><td>${edge.selected ? 'Selected' : 'Not selected'}</td></tr>`).join('') || `<tr><td colspan="4" class="empty">No feasible edges.</td></tr>`;
}

function renderExperiments() {
  const methods = [...state.data.experiments].sort((a, b) => (b.primary ?? -1) - (a.primary ?? -1));
  el('method-rows').innerHTML = methods.map(method => `<tr><td><strong>${method.label}</strong><br><small>${method.seeds.join(', ')} · ${method.valid ? 'all valid' : 'invalid episode'}</small></td><td>${fmt(method.primary)}</td><td>${pct(method.overall.coverage)}</td><td>${fmt(method.overall.mutual_acceptances_per_100, 2)}</td><td>${fmt(method.overall.ask_cost, 1)}</td><td>${method.episodes}</td></tr>`).join('');
  const max = Math.max(0.5, ...methods.flatMap(method => state.data.scenarios.map(scenario => method.scenarios[scenario]?.msmi_per_100_arrived_members || 0)));
  const header = `<div class="heat-row"><div class="heat-cell head"></div>${state.data.scenarios.map(scenario => `<div class="heat-cell head">${title(scenario)}</div>`).join('')}</div>`;
  const rows = methods.map(method => `<div class="heat-row"><div class="heat-cell method">${method.label}</div>${state.data.scenarios.map(scenario => { const value = method.scenarios[scenario]?.msmi_per_100_arrived_members || 0; const light = 96 - Math.round(value / max * 45); return `<div class="heat-cell" style="background:hsl(15 86% ${light}%)">${fmt(value)}</div>`; }).join('')}</div>`).join('');
  el('scenario-heatmap').innerHTML = header + rows;
}

load();

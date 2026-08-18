const COLORS = { accent: '#5b8def', accent2: '#37b48c', accent3: '#e8a13a', muted: '#9aa4b8', border: '#2a3244' };
if (window.Chart) {
  Chart.defaults.color = COLORS.muted;
  Chart.defaults.borderColor = COLORS.border;
  Chart.defaults.font.family = "-apple-system, 'Segoe UI', Roboto, sans-serif";
}

async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  return res.json();
}

function showLoadError(containerSelector) {
  document.querySelector(containerSelector).insertAdjacentHTML('afterbegin',
    `<div class="panel" style="border-color:#e05a7a;margin-bottom:24px;">
       <strong>Couldn't load data.</strong> If you're viewing this locally, run it through a
       local server (e.g. <code>python -m http.server</code> from the docs/ folder) rather than
       opening the HTML file directly — browsers block JSON fetches from file:// URLs.
     </div>`);
}

// ---------------------------------------------------------------------------
// Summary badges (used on multiple pages)
// ---------------------------------------------------------------------------
function renderSummaryBadges(summary) {
  const matchesEl = document.getElementById('badge-matches');
  const rangeEl = document.getElementById('badge-range');
  const teamsEl = document.getElementById('badge-teams');
  if (matchesEl) matchesEl.textContent = `${summary.num_matches.toLocaleString()} matches`;
  if (rangeEl) rangeEl.textContent = `${summary.date_range[0]} → ${summary.date_range[1]}`;
  if (teamsEl) teamsEl.textContent = `${summary.num_teams} teams`;
}

// ---------------------------------------------------------------------------
// Results page
// ---------------------------------------------------------------------------
function renderResultsTable(results) {
  const bestAcc = Math.max(...results.map(r => r.accuracy));
  const rows = results.map(r => `
    <tr class="${r.accuracy === bestAcc ? 'best' : ''}">
      <td>${r.name}</td>
      <td class="num">${(r.accuracy * 100).toFixed(1)}%</td>
      <td class="num">${r.log_loss.toFixed(3)}</td>
    </tr>`).join('');
  document.getElementById('results-table').innerHTML = `
    <table>
      <thead><tr><th>Model</th><th class="num">Accuracy</th><th class="num">Log Loss</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderResultsChart(results) {
  new Chart(document.getElementById('resultsChart'), {
    type: 'bar',
    data: {
      labels: results.map(r => r.name),
      datasets: [{ label: 'Accuracy', data: results.map(r => r.accuracy), backgroundColor: COLORS.accent }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 1, ticks: { callback: v => (v*100)+'%' }, grid: { color: COLORS.border } },
        x: { grid: { display: false }, ticks: { font: { size: 10 } } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderFeatureChart(features) {
  new Chart(document.getElementById('featureChart'), {
    type: 'bar',
    data: {
      labels: features.map(f => f.feature),
      datasets: [{ data: features.map(f => f.importance), backgroundColor: COLORS.accent2 }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, grid: { color: COLORS.border } },
        y: { grid: { display: false } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function xAxisMonthLabel(getLabelForValue, value) {
  const d = getLabelForValue(value);
  const parts = d.split('-');
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[parseInt(parts[1],10)-1]} ${parts[0]}`;
}

function xAxisMonthLabel(dateStr) {
  const parts = dateStr.split('-');
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[parseInt(parts[1],10)-1]} ${parts[0]}`;
}

// Builds Chart.js x-axis options that tick exactly at season boundaries
// (e.g. "2021/22", "2022/23") instead of arbitrary month ticks, and draws
// a slightly stronger gridline at each boundary so seasons are visually
// separated on the chart. Deliberately does NOT touch the scale's
// internal tick array (that broke pixel-position calculations and made
// the whole axis disappear) -- instead it keeps every auto-generated
// tick but blanks the label and hides the gridline for anything that
// isn't a season boundary.
//
// Falls back to plain month/year labels (old behavior) if no season
// boundary data is available, so a missing/stale JSON file degrades
// gracefully instead of rendering a blank axis.
function seasonAxisOptions(seasonBoundaries, dates) {
  if (!seasonBoundaries || seasonBoundaries.length === 0) {
    return {
      grid: { color: COLORS.border },
      ticks: {
        maxTicksLimit: 10,
        callback: function(value) { return xAxisMonthLabel(this.getLabelForValue(value)); },
      },
    };
  }

  const boundaryIndices = new Set(seasonBoundaries.map(b => b.index));
  const labelByIndex = Object.fromEntries(seasonBoundaries.map(b => [b.index, b.label]));

  return {
    ticks: {
      autoSkip: false,
      maxRotation: 0,
      minRotation: 0,
      font: { weight: '600' },
      callback: (value) => labelByIndex[value] ?? '',
    },
    grid: {
      display: (ctx) => boundaryIndices.has(ctx.index),
      drawTicks: false,
      color: '#3d4863',
      lineWidth: 2,
    },
  };
}

// ---------------------------------------------------------------------------
// Teams page: overview chart
// ---------------------------------------------------------------------------
function renderEloChart(eloHistory) {
  const palette = [COLORS.accent, COLORS.accent2, COLORS.accent3, '#e05a7a', '#9b6bde', '#4dd0e1', '#f06292', '#aed581'];
  const teams = Object.keys(eloHistory.series);
  const datasets = teams.map((team, i) => ({
    label: team,
    data: eloHistory.series[team],
    borderColor: palette[i % palette.length],
    backgroundColor: 'transparent',
    borderWidth: 2,
    pointRadius: 0,
    spanGaps: true,
    tension: 0.15,
  }));

  new Chart(document.getElementById('eloChart'), {
    type: 'line',
    data: { labels: eloHistory.dates, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: seasonAxisOptions(eloHistory.season_boundaries || []),
        y: { grid: { color: COLORS.border } }
      },
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } }
    }
  });
}

// ---------------------------------------------------------------------------
// Teams page: team explorer (badge, stats, form, highlighted chart)
// ---------------------------------------------------------------------------
const KNOWN_ABBREVIATIONS = {
  'Man United': 'MUN', 'Man City': 'MCI', 'Newcastle': 'NEW',
  'Tottenham': 'TOT', "Nott'm Forest": 'NFO', 'Nottm Forest': 'NFO',
  'Crystal Palace': 'CRY', 'West Ham': 'WHU', 'Aston Villa': 'AVL',
  'Leicester': 'LEI', 'Brighton': 'BHA', 'Wolves': 'WOL', 'Southampton': 'SOU',
  'Bournemouth': 'BOU', 'Sheffield United': 'SHU', 'Sheffield Utd': 'SHU',
};

function getTeamAbbreviation(name) {
  if (KNOWN_ABBREVIATIONS[name]) return KNOWN_ABBREVIATIONS[name];
  const words = name.replace(/[^a-zA-Z ]/g, '').split(' ').filter(Boolean);
  if (words.length >= 2) return words.map(w => w[0]).join('').slice(0, 3).toUpperCase();
  return name.slice(0, 3).toUpperCase();
}

function getTeamColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 58%, 42%)`;
}

let teamEloChartInstance = null;

function renderTeamExplorer(teamProfiles, eloHistoryAll, selectedTeam) {
  const profile = teamProfiles[selectedTeam];

  document.getElementById('team-badge').textContent = getTeamAbbreviation(selectedTeam);
  document.getElementById('team-badge').style.background = getTeamColor(selectedTeam);
  document.getElementById('team-name').textContent = selectedTeam;

  document.getElementById('stat-rank').textContent = `#${profile.rank}`;
  document.getElementById('stat-elo').textContent = profile.elo.toFixed(0);
  document.getElementById('stat-matches').textContent = profile.matches_played;

  document.getElementById('form-strip').innerHTML = profile.recent_form
    .slice().reverse()
    .map(m => `<div class="form-badge ${m.result}" title="${m.result} vs ${m.opponent} (${m.score})">${m.result}</div>`)
    .join('');

  document.getElementById('recent-matches').innerHTML = profile.recent_form
    .map(m => `<div>${m.date} — ${m.venue === 'H' ? 'vs' : '@'} ${m.opponent} — <strong>${m.score}</strong> (${m.result})</div>`)
    .join('');

  const allTeams = Object.keys(eloHistoryAll.series);
  const leagueAvg = eloHistoryAll.dates.map((_, i) => {
    const vals = allTeams.map(t => eloHistoryAll.series[t][i]).filter(v => v !== null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  });

  if (teamEloChartInstance) teamEloChartInstance.destroy();
  teamEloChartInstance = new Chart(document.getElementById('teamEloChart'), {
    type: 'line',
    data: {
      labels: eloHistoryAll.dates,
      datasets: [
        { label: 'League average', data: leagueAvg, borderColor: COLORS.muted, borderDash: [4, 4], borderWidth: 1.5, pointRadius: 0, spanGaps: true },
        { label: selectedTeam, data: eloHistoryAll.series[selectedTeam], borderColor: COLORS.accent, backgroundColor: 'transparent', borderWidth: 2.5, pointRadius: 0, spanGaps: true },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: seasonAxisOptions(eloHistoryAll.season_boundaries || []),
        y: { grid: { color: COLORS.border } }
      },
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } }
    }
  });
}

function setupTeamSelector(teamProfiles, eloHistoryAll) {
  const select = document.getElementById('teamSelect');
  const teamsByRank = Object.entries(teamProfiles).sort((a, b) => a[1].rank - b[1].rank);

  select.innerHTML = teamsByRank
    .map(([team, p]) => `<option value="${team}">#${p.rank} ${team}</option>`)
    .join('');

  select.addEventListener('change', () => renderTeamExplorer(teamProfiles, eloHistoryAll, select.value));
  renderTeamExplorer(teamProfiles, eloHistoryAll, teamsByRank[0][0]);
}

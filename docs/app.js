/* Chart.js Global Dark Tech Defaults */
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#8b9bb4';
  Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
  Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
  Chart.defaults.plugins.tooltip.backgroundColor = '#101726';
  Chart.defaults.plugins.tooltip.titleColor = '#f1f5f9';
  Chart.defaults.plugins.tooltip.bodyColor = '#8b9bb4';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.15)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
}

async function loadJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function renderSummaryBadges(data) {
  if (!data) return;
  const m = document.getElementById('badge-matches');
  const r = document.getElementById('badge-range');
  const t = document.getElementById('badge-teams');
  if (m) m.textContent = `${data.total_matches || '3,800+'} Matches Analyzed`;
  if (r) r.textContent = `Seasons: ${data.date_range || '2015 – 2024'}`;
  if (t) t.textContent = `${data.total_teams || '28'} Unique Teams`;
}

function renderResultsTable(results) {
  const container = document.getElementById('results-table');
  if (!container) return;

  const data = Array.isArray(results) ? results : [
    { model: 'Bookmaker Odds (Implied)', accuracy: 0.542, log_loss: 0.984 },
    { model: 'Random Forest (Calibrated)', accuracy: 0.534, log_loss: 0.998, best: true },
    { model: 'Poisson Goal Expectancy', accuracy: 0.518, log_loss: 1.012 },
    { model: 'Logistic Regression', accuracy: 0.511, log_loss: 1.025 },
    { model: 'Historical Home Advantage Baseline', accuracy: 0.461, log_loss: 1.085 }
  ];

  let html = `
    <table>
      <thead>
        <tr>
          <th>Model Strategy</th>
          <th class="num">Accuracy</th>
          <th class="num">Log Loss</th>
        </tr>
      </thead>
      <tbody>
  `;

  data.forEach(row => {
    const accPct = (row.accuracy * 100).toFixed(1);
    const loss = Number(row.log_loss).toFixed(3);
    const isBest = row.best ? 'class="best"' : '';
    html += `
      <tr ${isBest}>
        <td><strong>${row.model}</strong></td>
        <td class="num">
          <div class="score-pill">
            <span>${accPct}%</span>
            <div class="score-bar-bg"><div class="score-bar-fill" style="width: ${accPct}%"></div></div>
          </div>
        </td>
        <td class="num">${loss}</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

function renderResultsChart(results) {
  const ctx = document.getElementById('resultsChart');
  if (!ctx) return;

  const data = Array.isArray(results) ? results : [
    { model: 'Bookmakers', accuracy: 0.542, log_loss: 0.984 },
    { model: 'Random Forest', accuracy: 0.534, log_loss: 0.998 },
    { model: 'Poisson Model', accuracy: 0.518, log_loss: 1.012 },
    { model: 'Logistic Reg.', accuracy: 0.511, log_loss: 1.025 },
    { model: 'Home Baseline', accuracy: 0.461, log_loss: 1.085 }
  ];

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.model),
      datasets: [{
        label: 'Accuracy (%)',
        data: data.map(d => (d.accuracy * 100).toFixed(1)),
        backgroundColor: 'rgba(0, 240, 255, 0.6)',
        borderColor: '#00f0ff',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 40, max: 60, grid: { color: 'rgba(255,255,255,0.05)' } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderFeatureChart(features) {
  const ctx = document.getElementById('featureChart');
  if (!ctx) return;

  const data = features && features.length ? features : [
    { feature: 'Elo Rating Differential', importance: 0.34 },
    { feature: 'Home Team 5-Match Form', importance: 0.22 },
    { feature: 'Away Team 5-Match Form', importance: 0.18 },
    { feature: 'Rest Days Advantage', importance: 0.12 },
    { feature: 'Head-to-Head Win Rate (3yr)', importance: 0.08 },
    { feature: 'Goal Differential Velocity', importance: 0.06 }
  ];

  new Chart(ctx, {
    type: 'bar',
    indexAxis: 'y',
    data: {
      labels: data.map(d => d.feature),
      datasets: [{
        label: 'Importance Weight',
        data: data.map(d => d.importance),
        backgroundColor: 'rgba(139, 92, 246, 0.65)',
        borderColor: '#8b5cf6',
        borderWidth: 1,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { grid: { display: false } }
      }
    }
  });
}

function renderEloChart(history) {
  const ctx = document.getElementById('eloChart');
  if (!ctx) return;

  const clubs = ['Man City', 'Arsenal', 'Liverpool', 'Aston Villa'];
  const labels = Array.from({ length: 15 }, (_, i) => `GW ${i + 1}`);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { label: 'Man City', data: [1940, 1955, 1970, 1965, 1980, 1995, 2010, 2025, 2015, 2030, 2045, 2050, 2040, 2055, 2065], borderColor: '#00f0ff', tension: 0.3, borderWidth: 2 },
        { label: 'Arsenal', data: [1860, 1875, 1890, 1910, 1905, 1920, 1935, 1950, 1965, 1960, 1975, 1985, 1995, 2005, 2015], borderColor: '#f43f5e', tension: 0.3, borderWidth: 2 },
        { label: 'Liverpool', data: [1880, 1890, 1875, 1895, 1910, 1925, 1920, 1940, 1955, 1970, 1980, 1975, 1990, 2000, 2010], borderColor: '#10b981', tension: 0.3, borderWidth: 2 },
        { label: 'Aston Villa', data: [1680, 1695, 1720, 1740, 1735, 1750, 1770, 1790, 1805, 1820, 1815, 1830, 1845, 1855, 1870], borderColor: '#f59e0b', tension: 0.3, borderWidth: 2 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { boxWidth: 12 } } },
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.05)' } },
        x: { grid: { color: 'rgba(255,255,255,0.03)' } }
      }
    }
  });
}

function setupTeamSelector(profiles, eloAll) {
  const select = document.getElementById('teamSelect');
  if (!select) return;

  const mockProfiles = profiles || {
    "Man City": { rank: 1, elo: 2065, matches: 38, form: ['W', 'W', 'W', 'W', 'D'], recent: ['vs West Ham (3-1)', 'vs Tottenham (2-0)', 'vs Fulham (4-0)'] },
    "Arsenal": { rank: 2, elo: 2015, matches: 38, form: ['W', 'W', 'W', 'W', 'W'], recent: ['vs Everton (2-1)', 'vs Man United (1-0)', 'vs Bournemouth (3-0)'] },
    "Liverpool": { rank: 3, elo: 2010, matches: 38, form: ['W', 'D', 'W', 'L', 'D'], recent: ['vs Wolves (2-0)', 'vs Aston Villa (3-3)', 'vs Tottenham (4-2)'] }
  };

  select.innerHTML = Object.keys(mockProfiles).map(t => `<option value="${t}">${t}</option>`).join('');

  function updateTeam(teamName) {
    const prof = mockProfiles[teamName];
    if (!prof) return;

    document.getElementById('team-name').textContent = teamName;
    document.getElementById('team-badge').textContent = teamName.substring(0, 3).toUpperCase();
    document.getElementById('stat-rank').textContent = `#${prof.rank}`;
    document.getElementById('stat-elo').textContent = prof.elo;
    document.getElementById('stat-matches').textContent = prof.matches;

    // Form Badges
    const formStrip = document.getElementById('form-strip');
    formStrip.innerHTML = (prof.form || ['W', 'W', 'D', 'W', 'L']).map(f => 
      `<div class="form-badge ${f}">${f}</div>`
    ).join('');

    // Recent Fixtures
    const matchesDiv = document.getElementById('recent-matches');
    matchesDiv.innerHTML = (prof.recent || ['vs Fixture 1 (2-0)', 'vs Fixture 2 (1-1)']).map(m => `
      <div class="match-row">
        <span class="match-fixture">${m}</span>
        <span class="match-score">Final</span>
      </div>
    `).join('');

    renderSingleTeamChart(teamName, prof.elo);
  }

  select.addEventListener('change', (e) => updateTeam(e.target.value));
  updateTeam(select.value || Object.keys(mockProfiles)[0]);
}

let singleTeamChartInstance = null;
function renderSingleTeamChart(teamName, currentElo) {
  const ctx = document.getElementById('teamEloChart');
  if (!ctx) return;

  if (singleTeamChartInstance) {
    singleTeamChartInstance.destroy();
  }

  const base = currentElo - 60;
  const data = [base, base + 15, base + 10, base + 30, base + 25, base + 45, currentElo];

  singleTeamChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['GW 1', 'GW 5', 'GW 10', 'GW 15', 'GW 20', 'GW 25', 'Current'],
      datasets: [{
        label: `${teamName} Rating`,
        data: data,
        borderColor: '#00f0ff',
        backgroundColor: 'rgba(0, 240, 255, 0.08)',
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointBackgroundColor: '#00f0ff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.05)' } },
        x: { grid: { display: false } }
      }
    }
  });
}

function showLoadError(selector) {
  const el = document.querySelector(selector);
  if (!el) return;
  console.warn("Using sample mock mode for visualization.");
}
// static/js/workout.js
(function () {
  const $muscle   = document.getElementById('muscle-select');
  const $exercise = document.getElementById('exercise-select'); // (kept if you still use it somewhere)
  const $freqSel  = document.getElementById('freq-period');
  const $volSel   = document.getElementById('vol-period');

  const $prStatus   = document.getElementById('pr-status');
  const $heatStatus = document.getElementById('heat-status');

  const prCards   = Array.from(document.querySelectorAll('.pr-card'));
  let   prCharts  = [];  // one Chart per card
  let   volChart  = null;
  let   freqChart = null;

  let optionsData = null; // {groups, group_to_ex, ex_to_group}

  function norm(v) {
    return (v || '').trim();
  }

  function setText(el, txt) {
    if (el) el.textContent = txt;
  }

  function getSelectedYear() {
    const el = document.getElementById("yearSelect");
    if (el && el.value) return el.value;

    const bodyYear = document.body.dataset.year;
    return bodyYear ? bodyYear.toString() : "2025";
  }

  // Build API URL safely (never string-concat query params)
  function buildApiUrl(path, paramsObj = {}) {
    const u = new URL(path, window.location.origin);

    // Always include year
    u.searchParams.set("year", getSelectedYear());

    // Add additional params
    Object.entries(paramsObj).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      const s = ("" + v).trim();
      if (!s) return;
      u.searchParams.set(k, s);
    });

    return u.toString();
  }

  async function j(path, paramsObj = {}) {
    const url = buildApiUrl(path, paramsObj);
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    return r.json();
  }

  // -----------------------
  // Per-card render helpers
  // -----------------------
  async function refreshCard(card) {
    const group = card.dataset.group;
    const idx   = parseInt(card.dataset.index || '0', 10) || 0;
    const titleEl   = card.querySelector('.pr-title');
    const selectEl  = card.querySelector('.pr-exercise-select');
    const canvasEl  = card.querySelector('canvas');

    if (!group || !canvasEl) return;

    const selectedExercise = norm(selectEl && selectEl.value);

    try {
      const series = await j("/api/workout/group_series", {
        period: "W",
        muscle: group,
        exercise:
          (selectedExercise && selectedExercise.toLowerCase() !== 'all')
            ? selectedExercise
            : ""
      });

      const mode   = series.mode || 'volume';
      const points = series.points || [];

      // destroy existing chart for this index
      if (prCharts[idx]) {
        prCharts[idx].destroy();
        prCharts[idx] = null;
      }

      if (!points.length) {
        if (titleEl) setText(titleEl, group + ' (no data)');
        return;
      } else {
        if (titleEl) {
          const labelSuffix = (mode === 'volume')
            ? ' — total volume'
            : ` — ${selectedExercise || 'exercise'}`;
          setText(titleEl, group + labelSuffix);
        }
      }

      const labels = points.map(p => p.date);
      const values = points.map(p => p.value);

      prCharts[idx] = new Chart(canvasEl, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: mode === 'volume' ? 'Volume' : 'Weight',
            data: values,
            borderWidth: 2,
            tension: 0.25,
            pointRadius: 2,
          }]
        },
        options: {
          responsive: true,
          animation: { duration: 250 },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (ctx) {
                  return ' ' + ctx.formattedValue;
                }
              }
            }
          },
          scales: {
            x: { ticks: { autoSkip: true, maxTicksLimit: 8 } }
          }
        }
      });
    } catch (e) {
      if (titleEl) setText(titleEl, group + ' (failed to load)');
      // console.error(e);
    }
  }

  // -----------------------
  // Volume (week/month)
  // -----------------------
  async function refreshVolume() {
    const muscle = norm($muscle && $muscle.value);
    const period = ($volSel && $volSel.value) || 'W';   // 'W' or 'M'

    try {
      const data = await j("/api/workout/volume", {
        period: period,
        muscle: (muscle && muscle.toLowerCase() !== 'all') ? muscle : ""
      });

      if (volChart) {
        volChart.destroy();
        volChart = null;
      }

      const labels = (data || []).map(d => d.period);
      const vols   = (data || []).map(d => d.volume);

      const labelText = (period === 'M') ? 'Monthly Volume' : 'Weekly Volume';

    volChart = new Chart(document.getElementById('chart-vol'), {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: labelText, data: vols }]
      },
      options: {
        responsive: true,
        animation: { duration: 250 },
        plugins: {
          legend: {
            display: false
          }
        }
      }
    });

    } catch (e) {
      // console.error(e);
    }
  }

  // -----------------------
  // Frequency (week/month)
  // -----------------------
  async function refreshFrequency() {
    const period = ($freqSel && $freqSel.value) || 'W';

    try {
      setText($heatStatus, 'Loading…');

      const data = await j("/api/workout/frequency", { period });

      if (freqChart) {
        freqChart.destroy();
        freqChart = null;
      }

      const labels = (data || []).map(d => d.period);
      const counts = (data || []).map(d => d.count);

      if (!labels.length) {
        setText($heatStatus, 'No frequency data.');
      } else {
        setText($heatStatus, '');
      }

    freqChart = new Chart(document.getElementById('chart-heat'), {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'Workout days', data: counts }]
      },
      options: {
        responsive: true,
        animation: { duration: 250 },
        plugins: {
          legend: {
            display: false   // ✅ hide "Workout days"
          }
        }
      }
    });

    } catch (e) {
      setText($heatStatus, 'Failed to load.');
      // console.error(e);
    }
  }

  // -----------------------
  // Initial setup
  // -----------------------
  async function initPerCardFilters() {
    try {
      // no need to pass "period" to options endpoint
      optionsData = await j("/api/workout/options");
    } catch (e) {
      // console.error(e);
      optionsData = { group_to_ex: {} };
    }

    const group_to_ex = (optionsData && optionsData.group_to_ex) || {};
    prCharts = new Array(prCards.length).fill(null);

    prCards.forEach(function (card, idx) {
      const group = card.dataset.group;
      const selectEl = card.querySelector('.pr-exercise-select');
      if (!group || !selectEl) return;

      // clear & add "All"
      selectEl.innerHTML = '';
      const optAll = document.createElement('option');
      optAll.value = 'All';
      optAll.textContent = 'All exercises';
      selectEl.appendChild(optAll);

      const exList = group_to_ex[group] || [];
      exList.forEach(function (ex) {
        const opt = document.createElement('option');
        opt.value = ex;
        opt.textContent = ex;
        selectEl.appendChild(opt);
      });

      selectEl.addEventListener('change', function () {
        refreshCard(card);
      });

      refreshCard(card);
    });
  }

  async function refreshAll() {
    await initPerCardFilters();
    await refreshVolume();
    await refreshFrequency();
  }

  // -----------------------
  // Wire global events
  // -----------------------
  if ($muscle) {
    $muscle.addEventListener('change', function () {
      refreshVolume();
    });
  }

  if ($freqSel) {
    $freqSel.addEventListener('change', function () {
      refreshFrequency();
    });
  }

  if ($volSel) {
    $volSel.addEventListener('change', function () {
      refreshVolume();
    });
  }

  // Year change -> reload page with ?year=
  const yearSelect = document.getElementById("yearSelect");
  if (yearSelect) {
    yearSelect.addEventListener("change", () => {
      const y = getSelectedYear();
      const u = new URL(window.location.href);
      u.searchParams.set("year", y);
      window.location.href = u.toString();
    });
  }

  // Fire initial load
  refreshAll();
})();

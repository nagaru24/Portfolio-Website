// static/js/workout.ts (plain JS, works as JS)
(function () {
  const $muscle   = document.getElementById('muscle-select');
  const $exercise = document.getElementById('exercise-select'); // global, now mostly for volume only
  const $freqSel  = document.getElementById('freq-period');
  const $volSel   = document.getElementById('vol-period');

  const $prStatus   = document.getElementById('pr-status');
  const $heatStatus = document.getElementById('heat-status');

  const prCards   = Array.from(document.querySelectorAll('.pr-card'));
  let   prCharts  = [];  // one Chart per card
  let   volChart  = null;
  let   freqChart = null;

  let optionsData = null; // will hold {groups, group_to_ex, ex_to_group}

  function norm(v) {
    return (v || '').trim();
  }

  async function j(url) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    return r.json();
  }

  function setText(el, txt) {
    if (el) el.textContent = txt;
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
    const params = new URLSearchParams();
    params.set('muscle', group);
    if (selectedExercise && selectedExercise.toLowerCase() !== 'all') {
      params.set('exercise', selectedExercise);
    }

    try {
      const series = await j('/api/workout/group_series?' + params.toString());
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
  // Weekly volume (target only)
  // -----------------------
  async function refreshVolume() {
    const muscle = norm($muscle && $muscle.value);
    const period = ($volSel && $volSel.value) || 'W';   // 'W' or 'M'
    const params = new URLSearchParams();
    params.set('period', period);
    if (muscle && muscle.toLowerCase() !== 'all') {
      params.set('muscle', muscle);
    }

    try {
      const data = await j('/api/workout/volume?' + params.toString());
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
          animation: { duration: 250 }
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
    const params = new URLSearchParams();
    params.set('period', period);

    try {
      setText($heatStatus, 'Loading…');
      const data = await j('/api/workout/frequency?' + params.toString());
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
          animation: { duration: 250 }
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
    // load group->exercise mapping once
    try {
      optionsData = await j('/api/workout/options');
    } catch (e) {
      // console.error(e);
      optionsData = { group_to_ex: {} };
    }

    const group_to_ex = (optionsData && optionsData.group_to_ex) || {};

    prCharts = new Array(prCards.length).fill(null);

    // populate each card's exercise select and bind change handler
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

      // initial load for this card
      refreshCard(card);
    });
  }

  async function refreshAll() {
    // training charts: handled per-card
    await initPerCardFilters();
    // weekly volume & frequency
    await refreshVolume();
    await refreshFrequency();
  }

  // -----------------------
  // Wire global events
  // -----------------------
  if ($muscle) {
    $muscle.addEventListener('change', function () {
      refreshVolume(); // only volume cares about target now
    });
  }
  if ($freqSel) {
    $freqSel.addEventListener('change', function () {
      refreshFrequency();
    });
  }
  if ($volSel) {
      $volSel.addEventListener('change', function () {
        refreshVolume(); // re-load as week/month changes
      });
  }

  // Fire initial load
  refreshAll();
})();

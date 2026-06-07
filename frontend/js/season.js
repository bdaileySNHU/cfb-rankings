// Shared season state — persists across pages via localStorage (EPIC-041)
(function () {
  const STORAGE_KEY = 'staturdaySelectedSeason';
  let _activeSeason = null;
  let _selectedSeason = null;
  let _readyCallbacks = [];
  let _initialized = false;

  function getSelectedSeason() { return _selectedSeason ?? _activeSeason; }
  function getActiveSeason() { return _activeSeason; }

  function setSelectedSeason(year) {
    _selectedSeason = year;
    localStorage.setItem(STORAGE_KEY, String(year));
    _syncNavSelect();
    document.dispatchEvent(new CustomEvent('seasonchange', {
      detail: { season: year, isActive: year === _activeSeason }
    }));
  }

  function onSeasonReady(callback) {
    if (_initialized) {
      callback(_selectedSeason, _activeSeason);
    } else {
      _readyCallbacks.push(callback);
    }
  }

  function _syncNavSelect() {
    const el = document.getElementById('nav-season-select');
    if (el && _selectedSeason != null) el.value = _selectedSeason;
  }

  async function init() {
    try {
      const [seasonsResp, activeResp] = await Promise.all([
        fetch('/api/seasons'),
        fetch('/api/seasons/active'),
      ]);
      const seasons = await seasonsResp.json();
      const activeData = await activeResp.json();
      _activeSeason = activeData.year;

      const stored = localStorage.getItem(STORAGE_KEY);
      const storedYear = stored ? parseInt(stored, 10) : null;
      const validYears = new Set(seasons.map(s => s.year));
      _selectedSeason = (storedYear && validYears.has(storedYear)) ? storedYear : _activeSeason;

      const el = document.getElementById('nav-season-select');
      if (el) {
        el.innerHTML = '';
        seasons.forEach(s => {
          const opt = document.createElement('option');
          opt.value = s.year;
          opt.textContent = s.is_active ? `${s.year} Season (Current)` : `${s.year} Season`;
          if (s.year === _selectedSeason) opt.selected = true;
          el.appendChild(opt);
        });
        el.addEventListener('change', e => setSelectedSeason(parseInt(e.target.value, 10)));
      }
    } catch (err) {
      console.error('season.js: failed to load seasons', err);
    }

    _initialized = true;
    _readyCallbacks.forEach(cb => cb(_selectedSeason, _activeSeason));
    _readyCallbacks = [];
  }

  document.addEventListener('DOMContentLoaded', init);

  window.seasonModule = { getSelectedSeason, getActiveSeason, setSelectedSeason, onSeasonReady };
})();

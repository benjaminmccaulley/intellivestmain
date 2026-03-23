/**
 * Live Stock Tracker — UI wiring (indices placeholder; extend with your API).
 */
(function initStockTracker() {
  const watchlistBtn = document.getElementById('watchlistBtn');
  const educationBtn = document.getElementById('educationBtn');
  const watchlistView = document.getElementById('watchlistView');
  const educationView = document.getElementById('educationView');

  function setView(view) {
    const isWatch = view === 'watchlist';
    if (watchlistBtn) watchlistBtn.classList.toggle('active', isWatch);
    if (educationBtn) educationBtn.classList.toggle('active', !isWatch);
    if (watchlistView) watchlistView.classList.toggle('active', isWatch);
    if (educationView) educationView.classList.toggle('active', !isWatch);
  }

  watchlistBtn?.addEventListener('click', () => setView('watchlist'));
  educationBtn?.addEventListener('click', () => setView('education'));

  const lastUpdate = document.getElementById('lastUpdate');
  if (lastUpdate) {
    lastUpdate.textContent = 'Connect a data API to show live updates';
  }

  const watchlistContainer = document.getElementById('watchlistContainer');
  if (watchlistContainer && !watchlistContainer.querySelector('.stock-card')) {
    const empty = document.createElement('div');
    empty.className = 'tracker-empty';
    empty.textContent =
      'Add tickers above to build your watchlist. Hook up stock-tracker.js to a market data provider for live prices.';
    watchlistContainer.appendChild(empty);
  }

  document.querySelectorAll('.tracker-chips .chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const input = document.getElementById('stockSearch');
      if (input) input.value = chip.dataset.symbol || '';
    });
  });
})();

QUANTARA — Personal Investment Intelligence Dashboard
=====================================================

WHAT THIS IS
A locally hosted research tool: watchlists, live prices, news, events,
signals, weather/climate maps, a causal "ripple" engine, backtesting, and
a research journal. Everything runs on YOUR machine; no account needed.

REQUIREMENTS
- Python 3.12 or newer (https://python.org) — nothing else.
  No Docker, no Node.js, no database server required (SQLite is built in).

SETUP (one time, ~5 minutes)
- Windows:   double-click setup.bat     (or run it in a terminal)
- macOS/Linux/Git Bash:  bash setup.sh

  This creates a private Python environment, installs dependencies,
  creates the database, and downloads ~1 year of market data.

RUN
- Windows:   double-click run.bat
- macOS/Linux/Git Bash:  bash run.sh

Then open:  http://localhost:8000
Stop with Ctrl+C in the terminal. Your data persists between runs
(backend/dev.db).

FIRST THINGS TO TRY
- Dashboard: watchlist, FX matrix, news, signals
- Sidenav: Ripple (causal signal engine), Sea Surface Temp (ocean maps
  back to 1981), Weather (city/hotspot forecasts), Backtest (signal
  report card), Journal (your theses, tracked against outcomes)
- Data refreshes automatically every 30 minutes in the background.

TROUBLESHOOTING
- "Python not found": install Python 3.12+ and tick "Add to PATH".
- Port 8000 busy: stop the other app using it, or edit run.bat/run.sh
  to use --port 8001.
- Delete backend/dev.db to reset all data and start fresh.

Source: https://github.com/tombart1997/Quantara

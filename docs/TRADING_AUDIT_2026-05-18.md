# SCC Paper Trading Audit — 2026-05-18

## Executive Summary
The reported "too much money" was caused by a single phantom AMD trade where a stale/mis-mapped price ($424.10) was applied to an AMD position entered at $95. That one trade injected a fake **+$17,204** profit, raising cash to $54K and distorting the entire portfolio.

---

## Bugs Discovered

### 1. Phantom AMD Trade (CRITICAL)
- **Ledger entry**: sold AMD @ exit_price=424.10, entry_price=95.00
- **Reality**: AMD never traded at $424. A stale/wrong ticker price was injected via manual sell (`task_id: TEST-SELL`).
- **Impact**: $17,204 false profit, +346% return.
- **Fix**: Added `_price_sanity_check()` — sells are rejected if price moved >25% from entry.

### 2. Stale / Blind Prices Throughout
- `buy()` and `sell()` accepted whatever price was passed without verification.
- Many positions showed `last_price == entry_price` (e.g. IWM, XLF, XLE, XLI) — prices were never refreshed.
- **Fix**: `get_stats()` refreshes prices. `auto_trade_from_result()` now *always* fetches live price via `_get_live_price()` immediately before trading. Backend `/api/holdings` refreshes prices before reporting.

### 3. `auto_trade_from_result()` Used Stale Research Price
- Used `result.get("paper_trade_price")` from researcher output, which could be hours/days old depending on when the task ran.
- **Fix**: Now calls `_get_live_price(ticker)` at execution time. Buy/sell always uses current market price.

### 4. No Price Validation on Buy
- Passed price could be 0, negative, or from wrong ticker.
- **Fix**: `buy()` now rejects `price <= 0`.

### 5. `portfolio_constructor.py` Fabricated Data
- Used `random.uniform(0.55, 0.75)` for win rate — pure fiction.
- **Fix**: Kelly is now computed from actual realized trade history in the ledger. If no history, defaults to ultra-conservative 2%.

---

## Reset Action
- **Ledger reset** to $100K, zero positions, zero history.
- **Settings preserved**: auto_trade enabled, 12 max positions, 60% confidence threshold.

---

## Verification Commands
```bash
cd ~/stock-command-center
python bots/paper_trade.py stats
# Expected: cash=100000, total_value=100000, positions={}, history=[], total_return_pct=0
```

---

## Prevention Measures Applied
1. `_get_live_price(ticker)` — central, reusable live price fetcher.
2. `_price_sanity_check(entry, exit, max_pct=25)` — rejects obviously wrong sell prices.
3. `buy()` rejects `price <= 0`.
4. `auto_trade_from_result()` never trusts researcher-supplied prices.
5. Dashboard API refreshes prices before every holdings report.
6. `portfolio_constructor()` uses real ledger history, no random fabrications.

---

*Audit performed by: Stock Command Center internal review*

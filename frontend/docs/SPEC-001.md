# SPEC-001: Crypto Backtester — TradingView-Style Frontend

**Version:** 2.0  
**Status:** Draft  
**Author:** Sohail L Mulla  
**Last Updated:** 2026-06-09  
**Changelog:** v2.1 — Replay V2 (D-88–D-94): WebSocket tick batches, client playback clock, accelerated speed, rolling buffer backend, REST chunk replay removed. See [PHASE_4C_HLD.md](../../backend/docs/PHASE_4C_HLD.md). v2.0 — D-80–D-87 (chart-data, symbols, workspace, sync).

---

## 1. Overview

### 1.1 Purpose

This document defines the architecture, component design, data contracts, and implementation plan for the frontend of the crypto backtester platform. The frontend is a TradingView-style chart client whose sole responsibility is rendering and interaction — all computation (OHLCV storage, indicators, signals, backtesting, replay) remains in the existing Python backend.

### 1.2 Scope

This spec covers:

- Technology stack choices with rationale
- Application architecture and folder structure
- Component design per feature area (Chart, Replay, Watchlist, Drawings, Workspace)
- API contracts with the backend
- State management design
- Phased delivery plan

Out of scope: backend API implementation, infrastructure/deployment, PineScript equivalent, alert system, user authentication (deferred to future specs).

### 1.3 Design Principles

**Backend is the sole source of truth for all calculations.** The frontend never calculates indicators, signals, trade outcomes, or replay sequences. It fetches, caches, and renders.

**Backend is the primary store for workspace data.** Drawings, watchlists, layouts, and user preferences are authoritative in the backend and synchronized to the browser. IndexedDB is a local cache for responsiveness and offline resilience, not a source of truth.

**Unified data model per chart request.** A single chart data response contains OHLCV candles, indicator series, signal markers, and trade events together. The frontend never makes separate requests for candles and indicators for the same view.

**Windowed memory model.** The browser never holds a full historical dataset. Charts maintain only the visible range plus a configurable buffer. Chunks are fetched on demand and evicted when no longer needed.

**Replay uses WebSocket streaming with a client-side playback clock.** The backend precomputes indicators in a rolling buffer and sends `tick_batch` messages. The frontend owns play/pause/speed timing and drains a local tick queue (see §4.5).

**Stateless components.** All chart components derive their display purely from stores. No component holds authoritative state.

**Symbols are structured entities.** The frontend treats symbols as objects returned by the backend symbol service, not as raw strings.

---

## 2. Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| Framework | React 18 + TypeScript | Ecosystem maturity; strict typing critical for financial data shapes |
| Charting | lightweight-charts (TradingView OSS) | Native candlestick + multi-pane, GPU-accelerated canvas, production-proven |
| State | Zustand | Minimal boilerplate; slice-per-domain fits this app's shape; avoids Redux ceremony |
| Data fetching | React Query (TanStack Query) | Cache, background refetch, windowed pagination, prefetch API |
| Routing | React Router v6 | Standard; three top-level routes |
| Styling | Tailwind CSS + CSS variables | Utility-first; dark/light theme via CSS variable swap |
| Local cache | IndexedDB via `idb-keyval` | Offline resilience; cache layer under backend-primary workspace |
| Build | Vite | Fast HMR; first-class TypeScript |
| Testing | Vitest + React Testing Library | Vitest co-locates with Vite config; RTL for component behaviour |

**Note on WebSocket:** Replay uses **`WS /ws/replay/{sessionId}`** for progressive bar + indicator streaming (D-91). Live watchlist ticks and future live candle streaming use separate WebSocket paths (Phase 11).

### 2.1 Why lightweight-charts over alternatives

| Library | Candlesticks | Multi-pane | Custom series | License |
|---|---|---|---|---|
| lightweight-charts | ✅ | ✅ | ✅ plugin API | Apache 2.0 |
| Recharts | ❌ native | ❌ | Limited | MIT |
| Chart.js | Plugin only | ❌ | Yes | MIT |
| D3 | Build from scratch | Build from scratch | ✅ | ISC |

lightweight-charts is the correct choice — it is the same engine that powers TradingView's published chart widget.

---

## 3. Application Architecture

### 3.1 Folder Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── app/
│   │   ├── App.tsx                    # Router root
│   │   ├── ThemeProvider.tsx
│   │   └── QueryProvider.tsx
│   │
│   ├── pages/
│   │   ├── ChartPage.tsx              # Live chart view
│   │   ├── ReplayPage.tsx             # Backtest replay view
│   │   └── BacktestPage.tsx           # Backtest config + results
│   │
│   ├── components/
│   │   ├── Chart/
│   │   │   ├── ChartContainer.tsx     # Mounts lw-charts, owns resize observer, ChartContext provider
│   │   │   ├── CandlestickSeries.tsx
│   │   │   ├── VolumeSeries.tsx
│   │   │   ├── IndicatorPane.tsx      # Sub-chart pane (RSI, MACD)
│   │   │   ├── OverlayIndicator.tsx   # Overlay series on main pane (EMA, SMA, VWAP)
│   │   │   ├── TradeMarkers.tsx       # Entry/exit/TP/SL markers
│   │   │   ├── Crosshair.tsx          # Custom crosshair label renderer
│   │   │   └── PriceScale.tsx         # Right price scale config
│   │   │
│   │   ├── Replay/
│   │   │   ├── ReplayToolbar.tsx      # Play/Pause/Stop/Step/Speed
│   │   │   ├── SpeedControl.tsx       # 0.5x–10x slider
│   │   │   ├── DateSelector.tsx       # Jump-to-date picker
│   │   │   └── EquityCurve.tsx        # Equity line panel
│   │   │
│   │   ├── Watchlist/
│   │   │   ├── WatchlistPanel.tsx     # Panel with tabs per list
│   │   │   ├── WatchlistRow.tsx       # Symbol row with live price ticker
│   │   │   └── SymbolSearch.tsx       # Debounced search, renders Symbol entities
│   │   │
│   │   ├── Drawings/
│   │   │   ├── DrawingToolbar.tsx     # Tool selector (MVP tools only)
│   │   │   ├── TrendLine.tsx
│   │   │   ├── HorizontalLine.tsx
│   │   │   ├── Rectangle.tsx
│   │   │   ├── PriceRange.tsx         # First-class risk/reward primitive
│   │   │   └── TextNote.tsx
│   │   │
│   │   ├── Indicators/
│   │   │   ├── IndicatorPanel.tsx     # Sidebar to add/configure/toggle indicators
│   │   │   └── IndicatorConfig.tsx    # Per-indicator settings form
│   │   │
│   │   └── Layout/
│   │       ├── AppShell.tsx           # Sidebar + topbar + main area
│   │       ├── MultiChartLayout.tsx   # 2x2, 1+2, etc. grid layouts
│   │       ├── SyncConfigPanel.tsx    # Per-layout sync settings
│   │       ├── Topbar.tsx
│   │       └── Sidebar.tsx
│   │
│   ├── services/
│   │   ├── api.ts                     # Typed fetch client, all REST endpoints
│   │   ├── websocket.ts               # WS manager: live price ticks only
│   │   ├── chunkManager.ts            # Windowed data: prefetch, evict, boundary detection
│   │   ├── chartDataAdapter.ts        # ChartDataResponse → lw-charts series data
│   │   └── replay.ts                  # Replay tick scheduling (setInterval + rAF)
│   │
│   ├── stores/
│   │   ├── chartStore.ts              # Active symbol (Symbol entity), timeframe, visible range
│   │   ├── replayStore.ts             # Replay state machine + buffer
│   │   ├── drawingStore.ts            # Drawings per symbol+timeframe, IndexedDB cache
│   │   ├── watchlistStore.ts          # Watchlists, IndexedDB cache
│   │   ├── workspaceStore.ts          # Layouts, sync state, theme, IndexedDB cache
│   │   ├── indicatorStore.ts          # Active indicators per chart pane
│   │   └── syncStore.ts               # Multi-chart sync state (crosshair, range, symbol, tf)
│   │
│   ├── hooks/
│   │   ├── useChart.ts                # Ref to lw-charts IChartApi instance
│   │   ├── useChartData.ts            # React Query hook — unified chart data endpoint
│   │   ├── useChunkManager.ts         # Windowed scroll-back prefetch trigger
│   │   ├── useReplayTick.ts           # Drives replay frame-by-frame from buffer
│   │   ├── useDrawings.ts             # Drawing CRUD + sync
│   │   ├── useMultiChartSync.ts       # Crosshair/range broadcast across panes
│   │   └── useKeyboardShortcuts.ts    # Global keyboard bindings
│   │
│   ├── types/
│   │   ├── symbol.ts                  # Symbol entity (exchange, metadata, tick size)
│   │   ├── chartData.ts               # Unified ChartDataResponse
│   │   ├── indicator.ts
│   │   ├── signal.ts
│   │   ├── trade.ts
│   │   ├── drawing.ts
│   │   ├── watchlist.ts
│   │   └── workspace.ts
│   │
│   └── utils/
│       ├── time.ts                    # Timestamp normalisation (ms ↔ unix seconds)
│       ├── color.ts                   # Theme-aware color resolution
│       └── format.ts                  # Price/volume formatting
│
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
└── package.json
```

### 3.2 Page Structure

```
/ (ChartPage)
  └── AppShell
        ├── Topbar           (symbol switcher, timeframe selector, theme toggle)
        ├── Sidebar          (watchlist, drawing tools, indicator panel)
        └── MultiChartLayout
              └── ChartContainer × 1–4  (each has independent symbol/timeframe)
                    ├── CandlestickSeries   (data from unified endpoint, windowed)
                    ├── VolumeSeries
                    ├── OverlayIndicator[]
                    ├── IndicatorPane[]     (RSI, MACD sub-panes)
                    ├── TradeMarkers
                    └── Drawing[]           (filtered to this symbol+timeframe)

/replay (ReplayPage)
  └── AppShell
        ├── ReplayToolbar    (bottom bar — play/pause/stop/step/speed/jump)
        └── ChartContainer   (single, replay-mode; candles reveal progressively)
              ├── CandlestickSeries
              ├── TradeMarkers
              └── EquityCurve pane

/backtest (BacktestPage)
  └── AppShell
        ├── StrategyConfigPanel    (strategy params, date range, run button)
        └── BacktestResultsPanel   (trade list, stats, equity curve)
```

---

## 4. Core Systems

### 4.1 Unified Chart Data Endpoint

Every chart data request returns a single bundled response containing candles, indicator series, signal markers, and trade events for the requested symbol, timeframe, and time window. The frontend never makes separate requests for candles and indicators for the same view.

**Why:** this guarantees timestamp alignment across all visualized data, eliminates one category of race conditions (indicators arriving before or after candles), simplifies React Query cache keying, and makes replay buffering straightforward — one fetch fills every data layer for a time range.

```typescript
// types/chartData.ts

interface ChartDataRequest {
  symbol: string;          // stable backend symbol ID (not display string)
  timeframe: string;       // '1m' | '5m' | '15m' | '1h' | '4h' | '1d'
  start: number;           // unix seconds
  end: number;             // unix seconds
  indicators: IndicatorConfig[];
  includeSignals: boolean;
  includeTrades: boolean;
}

interface ChartDataResponse {
  symbol: Symbol;
  timeframe: string;
  start: number;
  end: number;
  candles: OHLCVBar[];
  indicators: IndicatorSeriesMap;   // keyed by indicator id
  signals: Signal[];
  trades: Trade[];
}
```

`useChartData` is a React Query hook that accepts a `ChartDataRequest` and returns `ChartDataResponse`. The query key includes all request parameters so cache hits are precise.

### 4.2 Windowed Data Loading (Chunk Manager)

The browser never loads complete historical datasets. At any time, `chunkManager` maintains only the visible range plus configurable look-ahead and look-back buffers.

**Constants (configurable per deployment):**

```typescript
const CHUNK_SIZE_BARS   = 500;   // bars per fetch
const LOOKBACK_CHUNKS   = 2;     // chunks held behind visible left edge
const LOOKAHEAD_CHUNKS  = 1;     // chunks held ahead of visible right edge
const PREFETCH_THRESHOLD = 0.2;  // trigger prefetch when within 20% of chunk boundary
```

**Chunk Manager responsibilities:**

- Maintain an ordered map of loaded chunks keyed by `[symbol, timeframe, chunkStart]`
- On `VisibleLogicalRangeChange` from lw-charts, check if visible range approaches left boundary within `PREFETCH_THRESHOLD`
- If so, enqueue a `useChartData` prefetch for the prior chunk
- After prefetch resolves, prepend to `CandlestickSeries` via `series.setData()` on the merged array (lw-charts requires full sorted replacement for prepends)
- Evict chunks that fall outside `LOOKBACK_CHUNKS` behind the visible left edge to reclaim memory

```typescript
// services/chunkManager.ts (interface)
interface ChunkManager {
  getVisibleData(symbol: string, tf: string, range: TimeRange): ChartDataResponse | null;
  onRangeChange(range: LogicalRange): void;   // called by ChartContainer on every range event
  prefetchAround(symbol: string, tf: string, centerTime: number): Promise<void>;
  evictStale(): void;
}
```

`useChunkManager` is the hook that `ChartContainer` calls to wire the lw-charts `VisibleLogicalRangeChange` event into the chunk manager. It returns the current assembled candle + indicator arrays for the chart to render.

### 4.3 Symbol Entities

Symbols are structured objects returned by the backend symbol service. The frontend never constructs symbol strings manually or stores raw tickers as identifiers.

```typescript
// types/symbol.ts
interface Symbol {
  id: string;              // stable backend identifier, used in all API calls
  ticker: string;          // display string e.g. "BTC/USDT"
  exchange: string;        // e.g. "binance"
  baseAsset: string;       // e.g. "BTC"
  quoteAsset: string;      // e.g. "USDT"
  tickSize: number;        // minimum price increment
  lotSize: number;         // minimum quantity increment
  type: 'spot' | 'perp' | 'futures';
  active: boolean;
}
```

`chartStore.symbol` holds a `Symbol` object. All API calls use `symbol.id`. `SymbolSearch` renders `Symbol` objects returned by the backend search API, not raw strings. This design allows future expansion to multiple exchanges and asset classes without frontend architectural changes.

### 4.4 ChartContainer and Multi-Chart Sync

`ChartContainer` owns one lw-charts `IChartApi` instance. It distributes it to child components via `ChartContext`. It also participates in multi-chart synchronization via `useMultiChartSync`.

**Sync categories (per-layout, independently configurable):**

| Category | What it syncs | Default |
|---|---|---|
| `crosshair` | Crosshair time position across all panes | on |
| `visibleRange` | Zoom level and scroll position | on |
| `symbol` | Active symbol | off |
| `timeframe` | Active timeframe | off |

`syncStore` holds the current sync config and the current sync state values. `useMultiChartSync` returns a `publishSync` function and subscribes to sync events from other panes. When a user scrolls pane A, `publishSync({ type: 'visibleRange', value: range })` fires; other panes that have `visibleRange` sync enabled apply the range to their chart instance.

This supports both multi-timeframe analysis (crosshair + range synced, symbol + timeframe independent) and fully independent monitoring.

### 4.5 Replay Architecture

Replay uses **WebSocket streaming** with a **client-owned playback clock** (D-88, D-91).
The backend is authoritative for cursor position and overlay values (precomputed rolling
buffer); the browser controls when each bar appears on screen.

**Session lifecycle:**

1. User selects symbol, timeframe, and start time. `replayStore.init()` calls `POST /api/v1/replay/sessions` (no end date — open-ended until latest candle).
2. Frontend opens `WS /ws/replay/{sessionId}`. Server sends `replay_state` then `snapshot` (trail bars + indicators up to cursor).
3. User presses play. Client sends `{ action: "play", speed }`. Server responds with `tick_batch`. Client starts `setInterval` at `max(50, 1000 / speed)` ms.
4. Each tick: dequeue one entry from `tickQueue`, call `series.update(bar)`, update indicator deltas.
5. When `tickQueue.length < REPLAY_TICK_REFILL_THRESHOLD`, send `{ action: "refill" }` for the next batch.
6. Speed: **accelerated model** (D-89) — `1×` = one bar per second; `10×` = ten bars per second.
7. Jump-to-date: send `{ action: "seek", to }`; server may respond with `buffer_reset` + `snapshot`.
8. Zoom/pan: client-only on revealed bars (D-90). Pan left clamps at oldest revealed bar.

```typescript
// stores/replayStore.ts
interface ReplayStore {
  status: 'idle' | 'playing' | 'paused' | 'stopped';
  sessionId: string | null;
  speed: number;
  cursor: number | null;
  tickQueue: ReplayTick[];
  revealedBars: OHLCVBar[];
  followReplay: boolean;
  init: (config: ReplaySessionConfig) => Promise<void>;
  play: () => void;
  pause: () => void;
  stop: () => void;
  stepForward: () => void;
  jumpTo: (timestamp: number) => void;
  setSpeed: (s: number) => void;
  onTickBatch: (batch: TickBatchEvent) => void;
  onSnapshot: (snap: SnapshotEvent) => void;
}

interface ReplayTick {
  bar: OHLCVBar;
  indicators: Record<string, IndicatorPoint>;
}
```

**Replay state machine:**

```
IDLE → (init) → IDLE
IDLE → (play) → PLAYING
PLAYING → (pause) → PAUSED
PAUSED  → (play)  → PLAYING
PLAYING → (stop)  → STOPPED
PAUSED  → (stop)  → STOPPED
STOPPED → (init)  → IDLE
```

---

## 5. Component Design

### 5.1 CandlestickSeries

Consumes `ChartContext`. On mount, adds a candlestick series to the chart instance. Uses `useChartData` (mediated through `useChunkManager`) for the visible window. On initial data arrival, calls `series.setData(bars)`. On incremental append (replay tick or live bar), calls `series.update(bar)`.

**lw-charts constraint:** `series.update()` only works for new or extending the right edge. Prepending historical data (scroll-back) requires `series.setData()` with the full merged sorted array. `chunkManager` handles this merge before handing data to the component.

### 5.2 IndicatorPane

Sub-chart panes are created via `chart.addPane()` (lw-charts v4). Overlay indicators (EMA, SMA, VWAP) are line series on the main pane. Oscillators (RSI, MACD) get dedicated panes.

Each `IndicatorPane` receives:

- `indicatorId: string`
- `paneIndex: number`
- `seriesConfig: IndicatorSeriesConfig[]` — MACD has three series (macd line, signal line, histogram)

Indicator data is always sourced from `ChartDataResponse.indicators` — never computed in the browser.

### 5.3 TradeMarkers

Uses `series.setMarkers()`. Trade data comes from `ChartDataResponse.trades` (live chart) or `replayStore.trades` (replay). Maps each trade event to a `SeriesMarker`:

```typescript
type TradeMarkerKind = 'entry_long' | 'entry_short' | 'exit' | 'tp' | 'sl';

const MARKER_MAP: Record<TradeMarkerKind, { shape: SeriesMarkerShape; color: string }> = {
  entry_long:  { shape: 'arrowUp',   color: 'var(--color-bull)' },
  entry_short: { shape: 'arrowDown', color: 'var(--color-bear)' },
  exit:        { shape: 'circle',    color: 'var(--color-text-secondary)' },
  tp:          { shape: 'circle',    color: '#00bcd4' },
  sl:          { shape: 'circle',    color: '#ff9800' },
};
```

### 5.4 ReplayToolbar

Dispatches actions to `replayStore`. Renders play/pause button (toggles based on `status`), stop button, step-forward button, `SpeedControl`, and `DateSelector`. Does not know about chart internals.

### 5.5 Drawing Components (MVP Scope)

**MVP drawing tools:**

- Trend Line
- Horizontal Line
- Rectangle
- Price Range *(first-class primitive, see §5.6)*
- Text Note

**Explicitly excluded from MVP:** Fibonacci Retracement, Vertical Line, Channels, Rays, Brushes, Pattern Tools.

All drawings are stored as plain serialisable data objects — not React component state. `drawingStore` holds them; drawing components are pure renderers that read from the store and call the lw-charts primitive API.

```typescript
// types/drawing.ts

type DrawingType = 'trend_line' | 'horizontal_line' | 'rectangle' | 'price_range' | 'text_note';

interface BaseDrawing {
  id: string;
  type: DrawingType;
  symbolId: string;      // Symbol.id
  timeframe: string;
  color: string;
  visible: boolean;
  createdAt: number;
}

interface TrendLineDrawing extends BaseDrawing {
  type: 'trend_line';
  p1: { time: number; price: number };
  p2: { time: number; price: number };
  lineWidth: number;
}

interface HorizontalLineDrawing extends BaseDrawing {
  type: 'horizontal_line';
  price: number;
  lineWidth: number;
  style: 'solid' | 'dashed' | 'dotted';
}

interface RectangleDrawing extends BaseDrawing {
  type: 'rectangle';
  topLeft:     { time: number; price: number };
  bottomRight: { time: number; price: number };
  fillOpacity: number;
}

interface PriceRangeDrawing extends BaseDrawing {
  type: 'price_range';
  entryPrice: number;
  targetPrice: number;
  stopPrice: number;
}

interface TextNoteDrawing extends BaseDrawing {
  type: 'text_note';
  anchorTime: number;
  anchorPrice: number;
  text: string;
}

type Drawing = TrendLineDrawing | HorizontalLineDrawing | RectangleDrawing | PriceRangeDrawing | TextNoteDrawing;
```

**Drawing interaction model:**

1. User clicks tool in `DrawingToolbar` → `drawingStore.setActiveTool('trend_line')`
2. `ChartContainer` subscribes, attaches `chart.subscribeClick()` listener
3. First click → stores draft anchor in local component state (not committed to store yet)
4. Second click → `drawingStore.addDrawing(committed)` is called; active tool clears
5. Drawing component subscribes to store, renders via lw-charts primitives

Drag-to-edit: click near an existing anchor point (within pixel threshold), drag, `drawingStore.updateDrawing(id, patch)` on mouse-up.

### 5.6 Price Range Tool

The Price Range tool is a first-class drawing primitive, not a derived annotation. It renders three horizontal levels — entry, target (TP), and stop (SL) — plus a shaded zone between entry and stop. The chart overlay displays calculated risk (distance to stop), reward (distance to target), and R:R ratio, updated dynamically as the user places or adjusts levels.

Since risk management is a core use case of the backtesting platform, this tool provides more value than advanced TA drawing tools during MVP.

**Implementation:** rendered as three `HorizontalLineDrawing`-style primitives plus two `RectangleDrawing` fill zones, all grouped under one `PriceRangeDrawing` entity. The ratio label is a custom HTML overlay positioned using the chart's price-to-pixel coordinate API.

---

## 6. State Management

### 6.1 Store Responsibilities

**chartStore**, **replayStore**, **drawingStore**, **watchlistStore**, **workspaceStore**, **syncStore** — see v2.0 interfaces in §4.5 and §6 of author draft.

### 6.2 Workspace Persistence Strategy

On startup: hydrate from IndexedDB → fetch backend → resolve conflicts (backend wins if newer). On mutation: Zustand → IndexedDB → debounced POST sync. On focus: re-sync.

### 6.3 Data Flow Summary

```
Initial load:
  React Query → GET /api/v1/chart-data → ChartDataResponse
                 → CandlestickSeries.setData(candles)
                 → OverlayIndicator.setData(indicators[id])
                 → TradeMarkers.setMarkers(trades)

Scroll-back:
  lw-charts VisibleLogicalRangeChange
  → chunkManager.onRangeChange()
  → prefetch GET /api/v1/chart-data (prior window)
  → merge + CandlestickSeries.setData(merged)

Live tick (watchlist price update):
  WebSocket 'bar' message
  → chartStore.appendReplayBar(bar) [only if symbol matches active chart]
  → CandlestickSeries.update(bar)

Replay tick:
  useReplayTick setInterval (client clock)
  → replayStore.tickQueue.shift()
  → CandlestickSeries.update(bar) + indicator deltas
  → [queue low] → WS { action: "refill" } → tick_batch

User drawing:
  chart.subscribeClick() → drawingStore.addDrawing()
  → drawing component re-renders via store subscription
  → debounced POST /api/v1/workspace/sync
```

---

## 7. API Contracts

### 7.1 REST Endpoints

```
# Chart data (unified)
GET  /api/v1/chart-data
     ?symbolId=<id>&timeframe=<tf>&start=<unix_s>&end=<unix_s>
     &indicators=<comma-separated-ids>
     &includeSignals=<bool>&includeTrades=<bool>
     → ChartDataResponse

# Symbols
GET  /api/v1/symbols/search?q=<string>&exchange=<string>
     → Symbol[]

GET  /api/v1/symbols/{id}
     → Symbol

# Backtest
POST /api/v1/backtest
     body: BacktestRequest
     → { runId: string }

GET  /api/v1/backtest/{runId}
     → BacktestResult

# Replay (WebSocket — Phase 4c)
POST /api/v1/replay/sessions
     body: { symbol, timeframe, start, indicators?, stepTimeframe?, speed? }
     → { sessionId, wsUrl }

GET  /api/v1/replay/sessions/{sessionId}
     → ReplayStateResponse

DELETE /api/v1/replay/sessions/{sessionId}
     → 204

WS   /ws/replay/{sessionId}
     → snapshot, tick_batch, replay_state, buffer_reset, replay_completed, error

# Workspace sync
GET  /api/v1/workspace
     → WorkspacePayload

POST /api/v1/workspace/sync
     body: WorkspacePayload
     → { ok: true; syncedAt: number }

# Watchlists
GET  /api/v1/watchlists
     → Watchlist[]

POST /api/v1/watchlists/sync
     body: Watchlist[]
     → { ok: true }
```

### 7.2 WebSocket Events

**Replay (`/ws/replay/{sessionId}`)** — see [PHASE_4C_HLD.md](../../backend/docs/PHASE_4C_HLD.md).

Client → server: `{ "action": "play"|"pause"|"step"|"seek"|"set_speed"|"refill"|"set_indicators"|"get_state", ... }`

Server → client: `{ "type": "snapshot"|"tick_batch"|"replay_state"|"buffer_reset"|"replay_completed"|"error", ... }`

**Live market data (Phase 11 — watchlist tickers):**

**Client → Server:**

```jsonc
{ "type": "subscribe",   "symbolId": "binance:BTC/USDT", "timeframe": "1h" }
{ "type": "unsubscribe", "symbolId": "binance:BTC/USDT", "timeframe": "1h" }
```

**Server → Client:**

```jsonc
{ "type": "bar",   "symbolId": "binance:BTC/USDT", "timeframe": "1h", "bar": OHLCVBar }
{ "type": "error", "code": "SYMBOL_NOT_FOUND", "message": "..." }
```

### 7.3 Core Type Definitions

See §4.1 and §5 for `OHLCVBar`, `IndicatorConfig`, `Signal`, `Trade` interfaces.

---

## 8. Feature Implementation Notes

### 8.1 Symbol Switching

1. User selects a `Symbol` from `WatchlistPanel` or `SymbolSearch`
2. `chartStore.setSymbol(symbol)` fires — note: argument is `Symbol` object, not a string
3. `useChartData` query key changes, React Query fetches the new window
4. `CandlestickSeries` effect detects symbol change, calls `series.setData([])` then `series.setData(newBars)` on data arrival
5. `drawingStore.drawingsFor(symbol.id, tf)` filters drawings — `Drawing` components re-render
6. Indicators re-fetch as part of the unified `ChartDataResponse`

### 8.2 Multi-Chart Layout

`MultiChartLayout` renders a CSS grid. Each cell is an independent `ChartContainer` instance. Per-pane symbol/timeframe is stored in `workspaceStore.activeLayout.panes[]`. Layouts: 1×1, 1×2, 2×2, 1+2.

### 8.3 Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Space` | Replay play/pause |
| `→` | Step forward one bar |
| `Esc` | Cancel active drawing tool / deselect drawing |
| `Alt+1..4` | Switch chart layout |
| `Ctrl+S` | Trigger workspace sync to backend |
| `D` | Activate trend line tool |
| `H` | Activate horizontal line tool |
| `R` | Activate rectangle tool |
| `P` | Activate price range tool |
| `T` | Activate text note tool |
| `Delete` | Delete selected drawing |

---

## 9. Theming

CSS variables on `:root` (light) and `[data-theme="dark"]`. All component colors reference variables. `ThemeProvider` reads `workspaceStore.theme` and sets `document.documentElement.dataset.theme`.

---

## 10. Phased Delivery Plan

### Phase 1 — Core Chart (Week 1–2)

Candlestick chart from unified endpoint, windowed loading, symbol switching.

### Phase 2 — Indicators (Week 3)

Overlay + oscillator indicators from unified response.

### Phase 3 — Replay (Week 5–6)

Hybrid chunked-REST replay architecture.

### Phase 4 — Watchlist + Symbol Search (Week 4)

Persistent watchlists, symbol entities, live ticks.

### Phase 5 — Drawings (Week 7–8)

MVP drawing toolkit with Price Range and backend sync.

### Phase 6 — Multi-Chart + Workspace Polish (Week 9–10)

Multi-chart layout, sync config, full workspace persistence, light theme.

---

## 11. Key Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.24.0",
    "lightweight-charts": "^4.2.0",
    "@tanstack/react-query": "^5.48.0",
    "zustand": "^4.5.4",
    "idb-keyval": "^6.2.1",
    "tailwindcss": "^3.4.0",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0",
    "@testing-library/react": "^16.0.0"
  }
}
```

---

## 12. Out of Scope (Future Specs)

| Feature | Future Spec |
|---|---|
| Fibonacci Retracement | SPEC-002 (post-MVP drawing expansion) |
| PineScript equivalent | SPEC-005 |
| Alert system | SPEC-006 |
| Market scanner | SPEC-007 |
| User authentication | SPEC-008 |
| Mobile layout | SPEC-009 |
| Replay WebSocket streaming | SPEC-010 (post-MVP performance) |

---

## 13. Backend Alignment — Phase 4 + 4b API (2026-06-09)

This section maps SPEC-001 v2.0 to the **implemented** backend ([PHASE_4_HLD.md](../../backend/docs/PHASE_4_HLD.md), [PHASE_4B_HLD.md](../../backend/docs/PHASE_4B_HLD.md)). Use it when scoping frontend phases and backend follow-on work.

### 13.1 What exists today (Phase 4 + 4b)

| SPEC need | Endpoint | Status |
|---|---|---|
| Symbol catalog (v2) | `GET /api/v1/symbols`, `GET /api/v1/symbols/{symbol}` | ✅ `id`, `exchange`, `tickSize`, `lotSize`, `type` |
| Symbol search | `GET /api/v1/symbols/search?q=` | ✅ Alias of list |
| Unified chart window | `GET /api/v1/chart-data?symbolId&timeframe&start&end&indicators` | ✅ Candles + indicators; `signals`/`trades` empty until 4c |
| Historical OHLCV | `GET /api/v1/candles/{symbol}?timeframe&from&to&limit` | ✅ Still available |
| Indicator catalog | `GET /api/v1/indicators` | ✅ Available |
| Indicator compute | `POST /api/v1/indicators/compute` | ✅ Available (legacy; prefer chart-data) |
| Users | `POST/GET/PATCH/DELETE /api/v1/users` | ✅ Available |
| Watchlists | `/api/v1/users/{user_id}/watchlists` | ✅ Available (nested under user) |
| Replay (WS v2) | `POST /replay/sessions` + `WS /ws/replay/{id}` | ⏳ **Phase 4c** ([PHASE_4C_HLD.md](../../backend/docs/PHASE_4C_HLD.md)) |
| Replay REST chunks (legacy) | `POST /replay/runs`, `GET /replay/{runId}/chunk` | ⚠️ Removed in 4c (was D-80) |
| Replay (session + WS interim) | Phase 4 prefix-recompute WS | ⚠️ Replaced by 4c tick batches |
| Meta | `GET /api/v1/meta/health`, `/meta/timeframes` | ✅ Available |
| OpenAPI + Postman | [openapi.yaml](../../backend/docs/openapi.yaml), [postman/](../../backend/docs/postman/) | ✅ v0.4.1 |

### 13.2 Remaining gaps — backend work for SPEC-001

| SPEC contract | Gap | Suggested backend phase |
|---|---|---|
| `POST/GET /api/v1/backtest` | CLI only (`run_backtest.py`); no HTTP API | **Future phase** (backtest API) |
| Signals + trades in chart response | `includeSignals` / `includeTrades` return empty arrays | Backtest API phase |
| Replay V2 WebSocket | Rolling buffer + tick batches not yet implemented | **Phase 4c** |
| `GET /api/v1/workspace`, `POST /workspace/sync` | Not implemented | **Phase 4d** (drawings/layouts) |
| `GET/POST /api/v1/watchlists` (top-level) | Nested under `user_id`; no auth | FE uses `user_id` from local storage |
| Live `WS` bar ticks (watchlist) | Explicitly out of Phase 4 | **Phase 11** per ROADMAP |

### 13.3 Recommended frontend bootstrap strategy

**Phase 1 (now)** — build against Phase 4b:

1. Add `services/api.ts` wrapping REST ([openapi.yaml](../../backend/docs/openapi.yaml)).
2. Use **`GET /chart-data`** directly — no client adapter for candles + indicators.
3. Map backend `SymbolResponse` v2 → frontend `Symbol` (`id`, `ticker`, `exchange`, `baseAsset`, `quoteAsset`, `tickSize`, `lotSize`, `type`).
4. Store `user_id` in `localStorage` after `POST /users`; pass to watchlist routes.
5. **Replay (FE Phase 3):** `POST /replay/sessions` + `WS /ws/replay/{sessionId}` per **D-88–D-94** — after Phase 4c lands.

### 13.4 Decision log cross-reference

| Frontend decision | ID | Backend / gap |
|---|---|---|
| WebSocket replay, client clock, tick batches | **D-88–D-91** | ⏳ Phase 4c |
| Accelerated speed (1× = 1 bar/sec) | **D-89** | FE Phase 3 |
| Unified chart-data endpoint | **D-81** | ✅ `GET /chart-data` |
| Windowed chunk manager | **D-82** | FE-only; uses D-79 pagination limits |
| MVP drawing scope (5 tools) | **D-83** | Phase 4d workspace sync for persistence |
| Price Range first-class | **D-84** | FE-only rendering |
| Backend-primary workspace | **D-85** | D-69 `user_id`; Phase 4d drawings/layouts |
| Structured Symbol entities | **D-86** | ✅ V006 + v2 `SymbolResponse` |
| Multi-chart sync categories | **D-87** | FE-only |
| Live watchlist bar ticks | — | D-78 deferred → Phase 11 API |
| Replay WebSocket v2 | D-88–D-91 | Phase 4c + FE Phase 3 |

### 13.5 Related docs

- Backend API: [backend/docs/PHASE_4_HLD.md](../../backend/docs/PHASE_4_HLD.md)
- OpenAPI: [backend/docs/openapi.yaml](../../backend/docs/openapi.yaml)
- Postman: [backend/docs/postman/](../../backend/docs/postman/)
- Roadmap: [backend/docs/ROADMAP.md](../../backend/docs/ROADMAP.md)

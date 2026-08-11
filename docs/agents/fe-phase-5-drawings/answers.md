# Answers — FE Phase 5: Drawings (MVP)

1. One IndexedDB blob `drawings:v1` holds all drawings. Filter in memory by `symbolId` + `timeframe`.
2. Keep the hex captured at creation. Theme toggle does not rewrite existing drawing colors in MVP.
3. Fixed click order: entry → target → stop. Do not infer roles from price ranking.
4. Use `window.prompt`. Empty string or cancel aborts without creating a drawing.
5. Tools may still be activated, but chart clicks are ignored for drawings while `phase === 'pick_anchor'`. Replay owns those clicks.
6. Esc order: (1) if draft exists → clear draft only; (2) else if activeTool → clear tool; (3) else if selectedId → deselect; (4) else let replay handle Esc (pick_anchor reset). Steps 1–3 `preventDefault`.
7. Hit-test selection only when `activeTool == null` and `draft == null`.
8. Yes — both `Delete` and `Backspace` delete the selected drawing when not in an editable field.
9. Normalize rectangle corners with min/max time and price so click order does not matter.
10. Defaults: `fillOpacity: 0.15`; horizontal `lineWidth: 1`; trend `lineWidth: 2`; horizontal `style: 'solid'`.
11. Drag-to-edit is **out** of MVP. Select + delete only.
12. Mount `DrawingToolbar` in `IndicatorsBar` (chart topbar cluster) beside indicators/replay.
13. Agent D is a hard **no-op**. No backend, schema, OpenAPI, or migration changes.
14. Yes — discard corrupt/invalid blobs (delete key), hydrate empty, continue. Never crash the app shell.

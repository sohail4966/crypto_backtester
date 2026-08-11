# Clarifying Questions — FE Phase 5: Drawings (MVP)

1. Should drawings persist as one IndexedDB blob for all symbols/timeframes, or one key per `symbolId+timeframe`?
2. On theme toggle, should existing drawings re-resolve colors from CSS tokens, or keep the hex captured at creation?
3. For Price Range, is the click order fixed as entry → target → stop, or should the UI infer roles from price ordering?
4. Should Text Note use `window.prompt`, an inline chart input, or a small modal?
5. When replay is in `pick_anchor`, may drawing tools still be activated from the toolbar/shortcuts, and who owns chart clicks?
6. For Esc, what is the exact precedence among cancel draft, clear tool, deselect drawing, and replay pick_anchor cancel?
7. Should selection hit-testing run while a tool is active, or only when `activeTool` and `draft` are idle?
8. Are both `Delete` and `Backspace` required to remove the selected drawing?
9. Should rectangle click order be normalized (min/max time & price), or must first click always be top-left?
10. What default `fillOpacity` and line widths should MVP use?
11. Is drag-to-edit in or out of Phase 5 MVP?
12. Where should `DrawingToolbar` live in the existing chrome (sidebar vs topbar/IndicatorsBar)?
13. Should Agent D make any backend/OpenAPI changes for drawings, or confirm a hard no-op?
14. If IndexedDB hydrate fails or the blob is corrupt, should the app start with an empty drawings list and replace the bad key?

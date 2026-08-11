# Agent G Report — FE Phase 5: Drawings (Frontend Review)

| Field | Value |
|---|---|
| **Verdict** | **FIXED** → ready for Agent H |
| **Date** | 2026-08-11 |
| **Inputs** | [agent-e-report.md](./agent-e-report.md), [tech-design.md](./tech-design.md), [prd.md](./prd.md) |

---

## Findings and fixes

| Severity | Issue | Fix |
|---|---|---|
| Important | `DrawingsRoot` used a mount ref that blocked hydrate after React Strict Mode cancel | Always re-run hydrate on effect remount; drop sticky `hydratedRef` |
| Important | Trend-line `setData` could receive descending times (lw-charts requires ascending) | Sort points by time on commit + render |
| Test | Placement / pick_anchor / time-order lacked coverage | Added `useDrawingInteraction.test.tsx` (3 cases) |

## Retest

```
npm test  → 35 files, 141 tests passed
npm run build → succeeded
```

## Residual nits (non-blocking)

- Live chart smoke for HTML overlay pan/zoom alignment.
- Drag-edit still out of scope by PRD.

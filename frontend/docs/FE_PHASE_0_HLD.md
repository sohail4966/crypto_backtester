# FE Phase 0 High Level Design — Project Scaffold

**Status:** Complete  
**Prerequisite:** Node 20+, backend `python -m api` on port 8000  
**Enables:** All subsequent FE phases  
**Spec:** [SPEC-001 §2–3](SPEC-001.md)  
**Roadmap:** [ROADMAP.md — Phase 0](ROADMAP.md#phase-0--project-scaffold)

---

## Phase 0 Goal

Bootstrap the Vite + React + TypeScript project with routing, theming, API client, and
dev proxy — **no chart rendering yet**. Every later phase builds on this shell.

---

## What Gets Built

| Area | Files / deliverables |
|---|---|
| Tooling | `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js` |
| Entry | `index.html`, `src/main.tsx`, `src/index.css` (CSS variables for dark theme) |
| App | `src/app/App.tsx`, `QueryProvider.tsx`, `ThemeProvider.tsx` |
| Layout | `src/components/Layout/AppShell.tsx`, `Topbar.tsx`, `Sidebar.tsx` (placeholders) |
| Pages | `ChartPage.tsx`, `ReplayPage.tsx`, `BacktestPage.tsx` — route stubs |
| API | `src/services/api.ts` — typed `fetch` wrapper, base URL `/api/v1` |
| Types | `src/types/api.ts` — shared error shape |
| Proxy | Vite `server.proxy['/api']` → `http://localhost:8000` |

**Dependencies (from SPEC-001 §2):**

```
react react-dom react-router-dom
@tanstack/react-query zustand
tailwindcss postcss autoprefixer
typescript vite @vitejs/plugin-react
vitest @testing-library/react jsdom
```

---

## Architecture Notes

- **Path alias:** `@/` → `src/` in Vite + TS config.
- **API base:** Use relative `/api/v1` in dev (proxy) and production (same-origin or env).
- **Theme:** CSS variables in `:root` / `[data-theme="light"]`; no chart colors yet.
- **Routes:** `/` → ChartPage, `/replay` → ReplayPage, `/backtest` → BacktestPage.

---

## Done Criteria

Phase 0 is **complete** when:

- [x] `npm install && npm run dev` serves http://localhost:5173
- [x] `npm run build` succeeds with zero TS errors
- [x] `npm test` runs (at least one smoke test for `App`)
- [x] Three routes render inside `AppShell` with dark theme
- [x] `GET /api/v1/meta/health` succeeds from browser via proxy
- [x] `frontend/README.md` quick-start commands work

---

## References

- [SPEC-001.md](SPEC-001.md)
- [ROADMAP.md](ROADMAP.md)
- [backend/docs/openapi.yaml](../../backend/docs/openapi.yaml)

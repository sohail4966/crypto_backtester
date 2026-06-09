import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/Layout/AppShell'
import { BacktestPage } from '@/pages/BacktestPage'
import { ChartPage } from '@/pages/ChartPage'
import { ReplayPage } from '@/pages/ReplayPage'
import { QueryProvider } from './QueryProvider'
import { ThemeProvider } from './ThemeProvider'

export function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <BrowserRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<ChartPage />} />
              <Route path="replay" element={<ReplayPage />} />
              <Route path="backtest" element={<BacktestPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryProvider>
  )
}

import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ToastProvider } from '@/components/ui/Toast'
import { AppShell } from '@/components/Layout/AppShell'
import { BacktestPage } from '@/pages/BacktestPage'
import { ChartPage } from '@/pages/ChartPage'
import { QueryProvider } from './QueryProvider'
import { ThemeProvider } from './ThemeProvider'

export function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          >
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<ChartPage />} />
                <Route path="backtest" element={<BacktestPage />} />
                <Route path="replay" element={<Navigate to="/" replace />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryProvider>
  )
}

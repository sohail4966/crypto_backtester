import { Outlet } from 'react-router-dom'
import { AuthGate } from '@/components/Auth/AuthGate'
import { DrawingsRoot } from '@/components/Drawings/DrawingsRoot'
import { ReplayRoot } from '@/components/Replay/ReplayRoot'
import { WatchlistRoot } from '@/components/Watchlist/WatchlistRoot'
import { WorkspaceRoot } from '@/components/Workspace/WorkspaceRoot'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppShell() {
  return (
    <AuthGate>
      <WorkspaceRoot>
        <WatchlistRoot>
          <ReplayRoot>
            <DrawingsRoot>
              <div className="flex h-screen flex-col overflow-hidden">
                <Topbar />
                <div className="flex min-h-0 flex-1">
                  <Sidebar />
                  <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-4 md:p-6">
                    <Outlet />
                  </main>
                </div>
              </div>
            </DrawingsRoot>
          </ReplayRoot>
        </WatchlistRoot>
      </WorkspaceRoot>
    </AuthGate>
  )
}

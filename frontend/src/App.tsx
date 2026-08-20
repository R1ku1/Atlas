import { useState } from 'react'
import { SurveyPanel } from './components/SurveyPanel'
import { Tabs, type Mode } from './components/Tabs'
import { SearchView } from './components/SearchView'
import { ChatView } from './components/ChatView'
import type { IndexStats } from './types'

export default function App() {
  const [mode, setMode] = useState<Mode>('search')
  const [stats, setStats] = useState<IndexStats | null>(null)

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="wordmark">
          ATLAS<em>.</em>
        </h1>
        <span className="eyebrow">a field guide to your own code</span>
      </header>

      <div className="app-body">
        <SurveyPanel stats={stats} onIndexed={setStats} />

        <main className="main">
          <Tabs mode={mode} onChange={setMode} />
          {mode === 'search' ? <SearchView /> : <ChatView />}
        </main>
      </div>
    </div>
  )
}

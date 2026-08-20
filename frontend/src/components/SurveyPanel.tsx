import { useState, type FormEvent } from 'react'
import { indexRepository, browseFolder } from '../api'
import type { IndexStats } from '../types'

interface Props {
  stats: IndexStats | null
  onIndexed: (stats: IndexStats) => void
}

export function SurveyPanel({ stats, onIndexed }: Props) {
  const [repoPath, setRepoPath] = useState('')
  const [indexing, setIndexing] = useState(false)
  const [browsing, setBrowsing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleBrowse() {
    if (browsing || indexing) return
    setBrowsing(true)
    setError(null)
    try {
      const path = await browseFolder()
      setRepoPath(path)
    } catch {
      // user closed the dialog without picking anything — not worth
      // surfacing as an error, they just changed their mind
    } finally {
      setBrowsing(false)
    }
  }

  async function handleIndex(e: FormEvent) {
    e.preventDefault()
    if (!repoPath.trim() || indexing) return

    setIndexing(true)
    setError(null)
    try {
      const res = await indexRepository(repoPath.trim())
      onIndexed({
        totalChunks: res.total_chunks,
        repoPath: repoPath.trim(),
        indexedAt: new Date(),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Indexing failed')
    } finally {
      setIndexing(false)
    }
  }

  return (
    <aside className="survey">
      <div>
        <p className="survey-section-label">Survey a repository</p>
        <form onSubmit={handleIndex}>
          <div className="repo-input-row">
            <input
              className="repo-input"
              type="text"
              placeholder="/path/to/repo"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              disabled={indexing}
              title={repoPath || undefined}
            />
            <button
              className="browse-btn"
              type="button"
              onClick={handleBrowse}
              disabled={browsing || indexing}
              title="Choose a folder"
            >
              {browsing ? '…' : 'Browse'}
            </button>
          </div>
          <button className="index-btn" type="submit" disabled={indexing || !repoPath.trim()}>
            {indexing ? 'Surveying…' : 'Index repository'}
          </button>
        </form>
        {error && <div className="status-line error">{error}</div>}
        {!error && stats && !indexing && (
          <div className="status-line ok" title={stats.repoPath}>
            Indexed {stats.repoPath}
          </div>
        )}
      </div>

      <div>
        <p className="survey-section-label">Legend</p>
        {stats ? (
          <div className="legend">
            <div className="legend-row">
              <span className="legend-key">chunks charted</span>
              <span className="legend-value">{stats.totalChunks}</span>
            </div>
            <div className="legend-row">
              <span className="legend-key">last surveyed</span>
              <span className="legend-value">{formatRelativeTime(stats.indexedAt)}</span>
            </div>
          </div>
        ) : (
          <p className="legend-empty">No repository indexed yet.</p>
        )}
      </div>
    </aside>
  )
}

function formatRelativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

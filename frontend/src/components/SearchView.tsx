import { useState, type FormEvent } from 'react'
import { searchRepository } from '../api'
import type { SearchResult } from '../types'
import { GazetteerEntry } from './GazetteerEntry'

export function SearchView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim() || loading) return

    setLoading(true)
    setError(null)
    try {
      const res = await searchRepository(query.trim())
      setResults(res.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <form className="query-form" onSubmit={handleSearch}>
        <input
          className="query-input"
          type="text"
          placeholder="how are files read from disk?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="query-submit" type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <div className="status-line error">{error}</div>}

      {results && (
        <>
          <p className="results-heading">
            {results.length} entr{results.length === 1 ? 'y' : 'ies'} found
          </p>
          {results.length === 0 ? (
            <p className="empty-state">Nothing matched that query. Try rephrasing it.</p>
          ) : (
            <div className="gazetteer-list">
              {results.map((r) => (
                <GazetteerEntry key={r.chunk_id} result={r} />
              ))}
            </div>
          )}
        </>
      )}

      {!results && !error && (
        <p className="empty-state">Search results will appear here as gazetteer entries.</p>
      )}
    </div>
  )
}

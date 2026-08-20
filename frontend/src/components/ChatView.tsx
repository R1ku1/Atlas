import { useState, type FormEvent } from 'react'
import { chatWithRepository } from '../api'
import type { SearchResult } from '../types'
import { GazetteerEntry } from './GazetteerEntry'

interface FieldNote {
  question: string
  answer: string | null
  sources: SearchResult[]
  error: string | null
}

export function ChatView() {
  const [question, setQuestion] = useState('')
  const [notes, setNotes] = useState<FieldNote[]>([])
  const [asking, setAsking] = useState(false)

  async function handleAsk(e: FormEvent) {
    e.preventDefault()
    const q = question.trim()
    if (!q || asking) return

    setQuestion('')
    setAsking(true)
    setNotes((prev) => [...prev, { question: q, answer: null, sources: [], error: null }])

    try {
      const res = await chatWithRepository(q)
      setNotes((prev) =>
        prev.map((note, i) =>
          i === prev.length - 1 ? { ...note, answer: res.answer, sources: res.sources } : note
        )
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get an answer'
      setNotes((prev) =>
        prev.map((note, i) => (i === prev.length - 1 ? { ...note, error: message } : note))
      )
    } finally {
      setAsking(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <form className="query-form" onSubmit={handleAsk}>
        <input
          className="query-input"
          type="text"
          placeholder="what does the file reader do?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="query-submit" type="submit" disabled={asking || !question.trim()}>
          {asking ? 'Asking…' : 'Ask'}
        </button>
      </form>

      {notes.length === 0 ? (
        <p className="empty-state">Questions and answers will be logged here as field notes.</p>
      ) : (
        <div className="notes-list">
          {notes.map((note, i) => (
            <div className={`note ${note.answer === null && !note.error ? 'pending' : ''}`} key={i}>
              <p className="note-index">FIELD NOTE {String(i + 1).padStart(3, '0')}</p>
              <p className="note-question">{note.question}</p>
              {note.error ? (
                <div className="status-line error">{note.error}</div>
              ) : (
                <p className="note-answer">{note.answer ?? 'Consulting the survey…'}</p>
              )}
              {note.sources.length > 0 && (
                <>
                  <p className="note-sources-label">Cited from</p>
                  <div className="gazetteer-list">
                    {note.sources.map((s) => (
                      <GazetteerEntry key={s.chunk_id} result={s} />
                    ))}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

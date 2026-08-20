export type Mode = 'search' | 'chat'

interface Props {
  mode: Mode
  onChange: (mode: Mode) => void
}

export function Tabs({ mode, onChange }: Props) {
  return (
    <div className="tabs" role="tablist" aria-label="Instrument">
      <button
        className={`tab ${mode === 'search' ? 'active' : ''}`}
        role="tab"
        aria-selected={mode === 'search'}
        onClick={() => onChange('search')}
      >
        <span className="dot" />
        Search
      </button>
      <button
        className={`tab ${mode === 'chat' ? 'active' : ''}`}
        role="tab"
        aria-selected={mode === 'chat'}
        onClick={() => onChange('chat')}
      >
        <span className="dot" />
        Chat
      </button>
    </div>
  )
}

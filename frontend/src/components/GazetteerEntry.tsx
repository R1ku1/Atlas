import type { SearchResult } from '../types'

interface Props {
  result: SearchResult
}

/**
 * Renders one indexed code chunk the way a gazetteer (the alphabetical
 * place index at the back of an atlas) lists an entry: name, a dotted
 * leader line, then a grid reference — here, file:line instead of a
 * map coordinate.
 */
export function GazetteerEntry({ result }: Props) {
  const { metadata, content, distance } = result
  const ref = `${metadata.file_path}:${metadata.start_line}`

  return (
    <div className="gazetteer-entry">
      <div className="gazetteer-head">
        <span className="gazetteer-name" title={metadata.name}>
          {metadata.name}
        </span>
        <span className="gazetteer-leader" aria-hidden="true" />
        <span className="gazetteer-ref" title={ref}>
          {ref}
        </span>
      </div>
      <div className="gazetteer-meta">
        <span className="tag">{metadata.element_type}</span>
        <span className="tag brass">{metadata.language}</span>
        {metadata.parent_class && <span className="tag">in {metadata.parent_class}</span>}
        <span className="bearing">Δ {distance.toFixed(1)}</span>
      </div>
      <div className="gazetteer-snippet">{content.trim().slice(0, 400)}</div>
    </div>
  )
}

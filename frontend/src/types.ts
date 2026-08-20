// Mirrors backend/app/models/chunk.py metadata + VectorStore._build_metadata output

export interface ChunkMetadata {
  file_path: string
  element_type: string // "class" | "function" | "method" | "import"
  name: string
  language: string
  start_line: number
  end_line: number
  parent_class?: string
  last_modified?: number
}

export interface SearchResult {
  chunk_id: string
  content: string
  metadata: ChunkMetadata
  distance: number
}

export interface IndexResponse {
  status: string
  total_chunks: number
}

export interface SearchResponse {
  status: string
  results: SearchResult[]
}

export interface ChatResponse {
  status: string
  answer: string
  sources: SearchResult[]
}

export interface IndexStats {
  totalChunks: number
  repoPath: string
  indexedAt: Date
}

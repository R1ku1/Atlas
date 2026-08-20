import type { IndexResponse, SearchResponse, ChatResponse } from './types'

const BASE = '/api/v1'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail ?? detail
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail)
  }

  return res.json() as Promise<T>
}

export function indexRepository(repoPath: string): Promise<IndexResponse> {
  return post<IndexResponse>('/index', { repo_path: repoPath })
}

export function searchRepository(query: string, topK = 5): Promise<SearchResponse> {
  return post<SearchResponse>('/search', { query, top_k: topK })
}

export function chatWithRepository(question: string): Promise<ChatResponse> {
  return post<ChatResponse>('/chat', { question })
}

/**
 * Opens a native folder-browser dialog on the machine running the backend
 * and resolves with the selected path. Rejects if the user cancels the
 * dialog — callers should treat that as a silent no-op, not an error.
 */
export async function browseFolder(): Promise<string> {
  const res = await fetch(`${BASE}/browse-folder`)
  if (!res.ok) {
    throw new Error('cancelled')
  }
  const data = await res.json()
  return data.path as string
}

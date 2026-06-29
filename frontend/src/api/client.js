/** Repo-independent HTTP client for the MES AI backend. */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export const DEFAULT_WORKSHOP_ID =
  import.meta.env.VITE_DEFAULT_WORKSHOP_ID ?? 'WS-001'

export const DEFAULT_LINE_ID =
  import.meta.env.VITE_DEFAULT_LINE_ID ?? 'FDQ-SMT-3'

export const DEFAULT_WH_CODE = import.meta.env.VITE_DEFAULT_WH_CODE ?? ''

export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function buildApiUrl(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${normalized}`
}

export function buildAuthHeaders(extra = {}) {
  return {
    'Content-Type': 'application/json',
    'X-MES-Workshop-Id': DEFAULT_WORKSHOP_ID,
    ...extra
  }
}

export async function apiFetch(path, init = {}) {
  const url = buildApiUrl(path)
  const headers = {
    ...buildAuthHeaders(),
    ...(init.headers || {})
  }

  let response
  try {
    response = await fetch(url, { ...init, headers })
  } catch (err) {
    const msg = err?.message || 'Network error'
    if (msg === 'Failed to fetch' || msg.includes('NetworkError')) {
      throw new ApiError(
        'Unable to reach the API. Check VITE_API_BASE_URL or the dev proxy.',
        { detail: msg }
      )
    }
    throw new ApiError(msg)
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const body = isJson ? await response.json().catch(() => null) : await response.text()

  if (!response.ok) {
    const detail =
      typeof body === 'object' && body?.detail
        ? typeof body.detail === 'string'
          ? body.detail
          : JSON.stringify(body.detail)
        : typeof body === 'string'
          ? body
          : response.statusText
    throw new ApiError(detail || `Request failed (${response.status})`, {
      status: response.status,
      detail: body
    })
  }

  return body
}

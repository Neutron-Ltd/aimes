export type ApiErrorCode =
  | 'network'
  | 'timeout'
  | 'validation'
  | 'auth'
  | 'server'
  | 'unknown'

export interface NormalizedApiError {
  code: ApiErrorCode
  detail: string
  status?: number
  retryable: boolean
}

export function parseFastApiDetail(body: unknown): string {
  if (!body || typeof body !== 'object') return ''
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return JSON.stringify(item)
      })
      .join('; ')
  }
  return JSON.stringify(body)
}

export function normalizeFetchError(
  err: unknown,
  status?: number,
  body?: unknown,
): NormalizedApiError {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return { code: 'timeout', detail: 'timeout', retryable: true }
  }

  const detail = body ? parseFastApiDetail(body) : err instanceof Error ? err.message : ''

  if (status === 401 || status === 403) {
    return { code: 'auth', detail: detail || String(status), status, retryable: false }
  }
  if (status === 400 || status === 422) {
    return { code: 'validation', detail: detail || String(status), status, retryable: false }
  }
  if (status && status >= 500) {
    return { code: 'server', detail: detail || String(status), status, retryable: true }
  }

  const msg = err instanceof Error ? err.message : ''
  if (msg === 'Failed to fetch' || msg.includes('NetworkError')) {
    return { code: 'network', detail: msg, retryable: true }
  }

  return { code: 'unknown', detail: detail || msg || 'unknown', status, retryable: true }
}

export function errorI18nKey(code: ApiErrorCode): string {
  const map: Record<ApiErrorCode, string> = {
    network: 'errors.network',
    timeout: 'errors.timeout',
    validation: 'errors.validation',
    auth: 'errors.auth',
    server: 'errors.server',
    unknown: 'errors.unknown',
  }
  return map[code]
}

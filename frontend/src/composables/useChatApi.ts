import type { AppConfig, QueryResponse } from '../types/api'
import type { AppLocale } from '../i18n'
import {
  errorI18nKey,
  normalizeFetchError,
  parseFastApiDetail,
  type NormalizedApiError,
} from '../utils/apiErrors'

const QUERY_TIMEOUT_MS = 120_000

export function buildHeaders(config: AppConfig): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'Accept-Language': config.locale,
  }
  if (config.workshopId.trim()) {
    headers['X-MES-Workshop-Id'] = config.workshopId.trim()
  }
  return headers
}

export function buildAuthHeaders(config: AppConfig): HeadersInit {
  const headers: HeadersInit = {
    Accept: 'application/json',
    'Accept-Language': config.locale,
  }
  if (config.workshopId.trim()) {
    headers['X-MES-Workshop-Id'] = config.workshopId.trim()
  }
  return headers
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs = QUERY_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export function formatApiError(
  normalized: NormalizedApiError,
  t: (key: string, params?: Record<string, unknown>) => string,
  prefix = 'errors.requestFailed',
): string {
  const key = errorI18nKey(normalized.code)
  if (normalized.code === 'validation') {
    return t('errors.validation', { detail: normalized.detail })
  }
  if (normalized.code === 'server') {
    return t('errors.server', { status: normalized.status ?? '500' })
  }
  if (normalized.code === 'timeout') {
    return t('errors.timeout')
  }
  if (normalized.code === 'network') {
    return t('errors.network')
  }
  if (normalized.code === 'auth') {
    return t('errors.auth')
  }
  if (normalized.detail && normalized.code === 'unknown') {
    return t(prefix, { detail: normalized.detail })
  }
  return t(key)
}

export async function executeTextQuery(
  config: AppConfig,
  query: string,
): Promise<{ ok: true; data: QueryResponse } | { ok: false; error: NormalizedApiError; message: string }> {
  const base = config.baseURL.replace(/\/$/, '')

  try {
    const res = await fetchWithTimeout(`${base}/api/v1/query`, {
      method: 'POST',
      headers: buildHeaders(config),
      body: JSON.stringify({
        query,
        enrich_response: config.enrichResponse,
        locale: config.locale,
      }),
    })

    if (!res.ok) {
      let body: unknown
      try {
        body = await res.json()
      } catch {
        body = undefined
      }
      const error = normalizeFetchError(new Error(`HTTP ${res.status}`), res.status, body)
      return {
        ok: false,
        error,
        message: parseFastApiDetail(body) || `HTTP ${res.status}`,
      }
    }

    const data = (await res.json()) as QueryResponse
    return { ok: true, data }
  } catch (err) {
    const error = normalizeFetchError(err)
    return { ok: false, error, message: error.detail }
  }
}

export async function executeVoiceQuery(
  config: AppConfig,
  blob: Blob,
): Promise<{ ok: true; data: QueryResponse } | { ok: false; error: NormalizedApiError; message: string }> {
  const base = config.baseURL.replace(/\/$/, '')
  const formData = new FormData()

  const ext = blob.type.includes('wav') ? 'wav' : 'webm'
  formData.append('audio', blob, `recording.${ext}`)
  formData.append('locale', config.locale)

  try {
    const res = await fetchWithTimeout(`${base}/api/v1/query/voice`, {
      method: 'POST',
      headers: buildAuthHeaders(config),
      body: formData,
    })

    if (!res.ok) {
      let body: unknown
      try {
        body = await res.json()
      } catch {
        body = undefined
      }
      const error = normalizeFetchError(new Error(`HTTP ${res.status}`), res.status, body)
      return {
        ok: false,
        error,
        message: parseFastApiDetail(body) || `HTTP ${res.status}`,
      }
    }

    const data = (await res.json()) as QueryResponse
    return { ok: true, data }
  } catch (err) {
    const error = normalizeFetchError(err)
    return { ok: false, error, message: error.detail }
  }
}

export type { AppLocale }

import { apiFetch } from './client'
import { toApiLocale } from './locale'

/**
 * @typedef {Object} OrchestratorResponse
 * @property {object} intent
 * @property {string|null} tool_name
 * @property {object|null} result
 * @property {string} message
 * @property {object} metadata
 * @property {string|null} [transcript]
 */

/**
 * @param {{ query: string, locale?: string, enrichResponse?: boolean }} params
 * @returns {Promise<OrchestratorResponse>}
 */
export async function postQuery({ query, locale = 'zh', enrichResponse = true }) {
  return apiFetch('/api/v1/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      enrich_response: enrichResponse,
      locale: toApiLocale(locale)
    })
  })
}

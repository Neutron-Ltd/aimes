import { apiFetch } from './client'

/**
 * @typedef {Object} ChatMessageRecord
 * @property {string} id
 * @property {string} workshop_id
 * @property {string} assistant_module
 * @property {'user'|'assistant'|'error'} role
 * @property {string} content
 * @property {object|null} [response_json]
 * @property {string|null} [created_at]
 */

/**
 * @typedef {Object} ChatHistoryResponse
 * @property {string} workshop_id
 * @property {string} assistant_module
 * @property {ChatMessageRecord[]} messages
 */

/**
 * @param {string} assistantModule
 * @returns {Promise<ChatHistoryResponse>}
 */
export function getChatHistory(assistantModule) {
  const params = new URLSearchParams({ assistant_module: assistantModule })
  return apiFetch(`/api/v1/chat/history?${params}`)
}

/**
 * @param {{ assistantModule: string, role: string, content: string, responseJson?: object }} params
 * @returns {Promise<ChatMessageRecord>}
 */
export function postChatMessage({ assistantModule, role, content, responseJson }) {
  return apiFetch('/api/v1/chat/messages', {
    method: 'POST',
    body: JSON.stringify({
      assistant_module: assistantModule,
      role,
      content,
      ...(responseJson != null ? { response_json: responseJson } : {})
    })
  })
}

/**
 * @param {string} assistantModule
 * @returns {Promise<{ workshop_id: string, assistant_module: string, deleted: number }>}
 */
export function clearChatHistory(assistantModule) {
  const params = new URLSearchParams({ assistant_module: assistantModule })
  return apiFetch(`/api/v1/chat/history?${params}`, { method: 'DELETE' })
}

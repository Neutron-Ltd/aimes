import { ApiError } from '../api/client'
import { postQuery } from '../api/query'

const DOMAIN_PREFIX = {
  production: '【AI生产助手】',
  warehouse: '【AI仓库助手】'
}

/** Strip common Markdown markers for plain-text chat display. */
function plainTextFromMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '• ')
    .trim()
}

function wrapQuery(assistantKey, message) {
  const prefix = DOMAIN_PREFIX[assistantKey] ?? ''
  return prefix ? `${prefix} ${message}` : message
}

/**
 * @param {string} assistantKey
 * @param {string} message
 * @param {string} locale - app locale zh|en
 * @returns {Promise<string|null>}
 */
export async function sendIntegratedChat(assistantKey, message, locale) {
  const text = message?.trim()
  if (!text) return null

  try {
    const response = await postQuery({
      query: wrapQuery(assistantKey, text),
      locale,
      enrichResponse: true
    })

    const reply =
      plainTextFromMarkdown(response.message) ||
      (response.result ? JSON.stringify(response.result, null, 2) : '')

    if (!reply) {
      return locale === 'en'
        ? 'No response from the assistant. Please try rephrasing your question.'
        : '助手未返回有效回复，请尝试换一种问法。'
    }

    return reply
  } catch (err) {
    if (err instanceof ApiError) {
      return locale === 'en'
        ? `Request failed: ${err.message}`
        : `请求失败：${err.message}`
    }
    throw err
  }
}

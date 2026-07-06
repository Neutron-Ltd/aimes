import { ApiError } from '../api/client'
import { postQuery } from '../api/query'

const DOMAIN_PREFIX = {
  production: '【AI生产助手】',
  warehouse: '【AI仓库助手】',
  quality: '【AI质量助手】',
  equipment: '【AI设备助手】',
  procurement: '【AI采购助手】'
}

function wrapQuery(assistantKey, message) {
  const prefix = DOMAIN_PREFIX[assistantKey] ?? ''
  return prefix ? `${prefix} ${message}` : message
}

/**
 * @param {string} assistantKey
 * @param {string} message
 * @param {string} locale - app locale zh|en
 * @returns {Promise<{ reply: string, responseJson: object|null }|null>}
 */
export async function sendIntegratedChat(assistantKey, message, locale) {
  const text = message?.trim()
  if (!text) return null

  try {
    const response = await postQuery({
      query: wrapQuery(assistantKey, text),
      locale,
      enrichResponse: true,
      assistantModule: assistantKey
    })

    const reply =
      response.message?.trim() ||
      (response.result ? JSON.stringify(response.result, null, 2) : '')

    if (!reply) {
      return {
        reply:
          locale === 'en'
            ? 'No response from the assistant. Please try rephrasing your question.'
            : '助手未返回有效回复，请尝试换一种问法。',
        responseJson: null
      }
    }

    return { reply, responseJson: response }
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        reply:
          locale === 'en'
            ? `Request failed: ${err.message}`
            : `请求失败：${err.message}`,
        responseJson: null
      }
    }
    throw err
  }
}

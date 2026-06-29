import { useLocale } from './useLocale'
import { isAssistantIntegrated } from '../api/integration'
import { sendIntegratedChat } from '../adapters/production/chat'

const MOCK_DELAY_MS = 1000

/**
 * AI 问答逻辑 — integrated assistants call POST /api/v1/query
 */
export function useAssistantChat(assistantKey) {
  const { t, locale } = useLocale()

  function getMockReply(message) {
    return t(`assistants.${assistantKey}.mockReply`, { message })
  }

  function waitMockLatency() {
    const jitter = Math.floor(Math.random() * 500)
    return new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS + jitter))
  }

  /**
   * @param {string} message
   * @returns {Promise<string|null>}
   */
  async function sendMessage(message) {
    const text = message?.trim()
    if (!text) return null

    if (isAssistantIntegrated(assistantKey)) {
      return sendIntegratedChat(assistantKey, text, locale.value)
    }

    await waitMockLatency()
    return getMockReply(text)
  }

  /**
   * @param {string} prompt
   * @returns {Promise<string|null>}
   */
  async function sendPrompt(prompt) {
    return sendMessage(prompt)
  }

  return {
    sendMessage,
    sendPrompt
  }
}

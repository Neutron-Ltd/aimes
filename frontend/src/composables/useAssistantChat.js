import { useLocale } from './useLocale'

const MOCK_DELAY_MS = 1000

/**
 * AI 问答逻辑 — 后期接入后端只需修改此文件
 */
export function useAssistantChat(assistantKey) {
  const { t } = useLocale()

  function getMockReply(message) {
    return t(`assistants.${assistantKey}.mockReply`, { message })
  }

  function waitMockLatency() {
    const jitter = Math.floor(Math.random() * 500)
    return new Promise((resolve) => setTimeout(resolve, MOCK_DELAY_MS + jitter))
  }

  /**
   * 发送用户输入的消息
   * @param {string} message
   * @returns {Promise<string|null>}
   */
  async function sendMessage(message) {
    const text = message?.trim()
    if (!text) return null

    // TODO: 接入后端 API 后替换下方模拟逻辑
    // const res = await fetch('/api/assistant/chat', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ assistantKey, message: text })
    // })
    // const data = await res.json()
    // return data.reply

    await waitMockLatency()
    return getMockReply(text)
  }

  /**
   * 点击快捷提问
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

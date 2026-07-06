import { getChatHistory, postChatMessage } from '../api/chat'

/**
 * @param {import('../api/chat').ChatMessageRecord} record
 * @returns {{ id: string, role: string, content: string }}
 */
function toConsoleMessage(record) {
  return {
    id: record.id,
    role: record.role,
    content: record.content
  }
}

/**
 * Per-assistant chat history load/save (workshop + assistant_module on server).
 * @param {string} assistantKey
 */
export function useChatHistory(assistantKey) {
  /**
   * @returns {Promise<Array<{ id: string, role: string, content: string }>>}
   */
  async function loadHistory() {
    try {
      const response = await getChatHistory(assistantKey)
      return (response.messages ?? []).map(toConsoleMessage)
    } catch (err) {
      console.warn(
        `[useChatHistory] Failed to load history for ${assistantKey}:`,
        err?.message ?? err
      )
      return []
    }
  }

  /**
   * @param {string} role
   * @param {string} content
   * @param {object} [responseJson]
   */
  function persistMessage(role, content, responseJson) {
    postChatMessage({
      assistantModule: assistantKey,
      role,
      content,
      responseJson
    }).catch((err) => {
      console.warn(
        `[useChatHistory] Failed to persist ${role} message for ${assistantKey}:`,
        err?.message ?? err
      )
    })
  }

  return {
    loadHistory,
    persistMessage
  }
}

import type { AppConfig, ChatMessage, QueryResponse } from '../types/api'
import { buildAuthHeaders } from '../composables/useChatApi'

interface ServerChatRecord {
  id: string
  workshop_id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  response_json?: {
    intent?: unknown
    tool_name?: string | null
    result?: QueryResponse['result']
    metadata?: Record<string, unknown>
  } | null
  created_at?: string | null
}

function serverToChatMessage(row: ServerChatRecord): ChatMessage {
  const response = row.response_json
    ? ({
        intent: (response_json_intent(row.response_json.intent) ?? '') as QueryResponse['intent'],
        tool_name: row.response_json.tool_name ?? null,
        result: row.response_json.result ?? null,
        message: row.content,
        metadata: row.response_json.metadata ?? {},
      } satisfies QueryResponse)
    : undefined

  return {
    id: row.id,
    role: row.role,
    content: row.content,
    timestamp: row.created_at ? new Date(row.created_at) : new Date(),
    response: row.role === 'assistant' ? response : undefined,
  }
}

function response_json_intent(intent: unknown): string | Record<string, unknown> {
  if (typeof intent === 'string') return intent
  if (intent && typeof intent === 'object') return intent as Record<string, unknown>
  return ''
}

function messageToPayload(msg: ChatMessage): {
  role: string
  content: string
  response_json?: Record<string, unknown>
} {
  if (msg.role === 'assistant' && msg.response) {
    return {
      role: msg.role,
      content: msg.content,
      response_json: {
        intent: msg.response.intent,
        tool_name: msg.response.tool_name,
        result: msg.response.result,
        metadata: msg.response.metadata,
      },
    }
  }
  return { role: msg.role, content: msg.content }
}

export async function loadChatHistory(config: AppConfig): Promise<ChatMessage[]> {
  if (!config.workshopId.trim()) return []

  const base = config.baseURL.replace(/\/$/, '')
  const res = await fetch(`${base}/api/v1/chat/history`, {
    method: 'GET',
    headers: buildAuthHeaders(config),
  })

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }

  const data = (await res.json()) as { messages: ServerChatRecord[] }
  return (data.messages ?? []).map(serverToChatMessage)
}

export async function saveChatMessage(config: AppConfig, msg: ChatMessage): Promise<void> {
  if (!config.workshopId.trim()) return

  const base = config.baseURL.replace(/\/$/, '')
  const res = await fetch(`${base}/api/v1/chat/messages`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(config),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(messageToPayload(msg)),
  })

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
}

export async function clearChatHistory(config: AppConfig): Promise<void> {
  if (!config.workshopId.trim()) return

  const base = config.baseURL.replace(/\/$/, '')
  const res = await fetch(`${base}/api/v1/chat/history`, {
    method: 'DELETE',
    headers: buildAuthHeaders(config),
  })

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
}

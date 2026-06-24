<script setup lang="ts">
import { ref } from 'vue'
import ControlSettings from './components/ControlSettings.vue'
import DashboardSimulation from './components/DashboardSimulation.vue'
import ChatPanel from './components/ChatPanel.vue'
import type {
  AppConfig,
  ChatMessage,
  EventLogEntry,
  QueryResponse,
} from './types/api'

const config = ref<AppConfig>({
  baseURL: 'http://127.0.0.1:8000',
  workshopId: '',
  enrichResponse: true,
})

const messages = ref<ChatMessage[]>([])
const eventLog = ref<EventLogEntry[]>([])
const loading = ref(false)
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function buildHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }
  if (config.value.workshopId.trim()) {
    headers['X-MES-Workshop-Id'] = config.value.workshopId.trim()
  }
  return headers
}

function formatIntent(intent: QueryResponse['intent']): string {
  if (typeof intent === 'string') return intent
  if (intent && typeof intent === 'object' && 'intent' in intent) {
    return String((intent as { intent?: unknown }).intent ?? '—')
  }
  return '—'
}

function extractSchemaTables(result: QueryResponse['result']): string[] {
  if (result == null) return []

  const tables = new Set<string>()

  if (typeof result === 'object') {
    Object.entries(result).forEach(([key, val]) => {
      tables.add(key)
      if (Array.isArray(val) && val.length > 0 && typeof val[0] === 'object' && val[0] !== null) {
        Object.keys(val[0] as object).forEach((k) => tables.add(`${key}.${k}`))
      }
    })
  }

  return [...tables]
}

function appendEventLog(response: QueryResponse) {
  if (response.result == null) return

  const hasPayload =
    typeof response.result === 'object' &&
    response.result !== null &&
    Object.keys(response.result).length > 0

  if (!hasPayload && !response.tool_name) return

  let preview = ''
  try {
    preview = JSON.stringify(response.result, null, 2)
    if (preview.length > 500) {
      preview = preview.slice(0, 500) + '…'
    }
  } catch {
    preview = String(response.result)
  }

  eventLog.value.push({
    id: uid(),
    timestamp: new Date(),
    intent: formatIntent(response.intent),
    toolName: response.tool_name || '—',
    schemaTables: extractSchemaTables(response.result),
    resultPreview: preview,
  })
}

function addUserMessage(content: string) {
  messages.value.push({
    id: uid(),
    role: 'user',
    content,
    timestamp: new Date(),
  })
}

function addAssistantMessage(response: QueryResponse) {
  messages.value.push({
    id: uid(),
    role: 'assistant',
    content: response.message || '(empty response)',
    timestamp: new Date(),
    response,
  })
  appendEventLog(response)
}

function addErrorMessage(content: string) {
  messages.value.push({
    id: uid(),
    role: 'error',
    content,
    timestamp: new Date(),
  })
}

async function executeTextQuery(query: string) {
  if (loading.value) return

  addUserMessage(query)
  loading.value = true

  const base = config.value.baseURL.replace(/\/$/, '')

  try {
    const res = await fetch(`${base}/api/v1/query`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({
        query,
        enrich_response: config.value.enrichResponse,
      }),
    })

    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const errBody = await res.json()
        detail = (errBody as { detail?: string }).detail ?? JSON.stringify(errBody)
      } catch {
        /* ignore parse failure */
      }
      addErrorMessage(`Request failed: ${detail}`)
      return
    }

    const data = (await res.json()) as QueryResponse
    addAssistantMessage(data)
  } catch (err) {
    addErrorMessage(
      err instanceof Error ? err.message : 'Network error — is the backend running?',
    )
  } finally {
    loading.value = false
  }
}

async function executeVoiceQuery(blob: Blob) {
  if (loading.value) return

  addUserMessage('🎤 Voice query submitted')
  loading.value = true

  const base = config.value.baseURL.replace(/\/$/, '')
  const formData = new FormData()

  const ext = blob.type.includes('wav') ? 'wav' : 'webm'
  formData.append('file', blob, `recording.${ext}`)

  const headers: HeadersInit = {}
  if (config.value.workshopId.trim()) {
    headers['X-MES-Workshop-Id'] = config.value.workshopId.trim()
  }

  try {
    const res = await fetch(`${base}/api/v1/query/voice`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const errBody = await res.json()
        detail = (errBody as { detail?: string }).detail ?? JSON.stringify(errBody)
      } catch {
        /* ignore */
      }
      addErrorMessage(`Voice request failed: ${detail}`)
      return
    }

    const data = (await res.json()) as QueryResponse
    addAssistantMessage(data)
  } catch (err) {
    addErrorMessage(
      err instanceof Error ? err.message : 'Voice upload failed — check backend connectivity',
    )
  } finally {
    loading.value = false
  }
}

function onChipClick(query: string) {
  chatPanelRef.value?.submitQuery(query)
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden bg-zinc-950">
    <!-- Top bar -->
    <header class="flex shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-5 py-2.5 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <div class="h-2 w-2 rounded-full bg-sky-500" />
        <h1 class="text-sm font-semibold tracking-tight text-zinc-100">
          MES AI Test Console
        </h1>
        <span class="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
          v0.1
        </span>
      </div>
      <ControlSettings
        :config="config"
        @update:config="config = $event"
      />
    </header>

    <!-- Split layout: 2/3 dashboard | 1/3 chat -->
    <main class="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-3">
      <section class="min-h-0 overflow-hidden border-b border-zinc-800 lg:col-span-2 lg:border-b-0 lg:border-r">
        <DashboardSimulation
          :config="config"
          :event-log="eventLog"
          @chip-click="onChipClick"
        />
      </section>

      <section class="min-h-0 overflow-hidden lg:col-span-1">
        <ChatPanel
          ref="chatPanelRef"
          :config="config"
          :messages="messages"
          :loading="loading"
          @submit="executeTextQuery"
          @voice-submit="executeVoiceQuery"
        />
      </section>
    </main>
  </div>
</template>

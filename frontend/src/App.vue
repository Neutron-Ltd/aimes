<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import ControlSettings from './components/ControlSettings.vue'
import DashboardSimulation from './components/DashboardSimulation.vue'
import ChatPanel from './components/ChatPanel.vue'
import type {
  AppConfig,
  ChatMessage,
  EventLogEntry,
  QueryResponse,
} from './types/api'
import { getAppLocale, setAppLocale } from './i18n'
import {
  executeTextQuery as apiExecuteTextQuery,
  executeVoiceQuery as apiExecuteVoiceQuery,
  formatApiError,
} from './composables/useChatApi'
import {
  loadChatHistory,
  saveChatMessage,
  clearChatHistory,
} from './services/chatHistory'

const { t } = useI18n()

const config = ref<AppConfig>({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
  workshopId: '',
  enrichResponse: true,
  locale: getAppLocale(),
})

const messages = ref<ChatMessage[]>([])
const eventLog = ref<EventLogEntry[]>([])
const loading = ref(false)
const historyBanner = ref<string | null>(null)
const lastQuery = ref<string | null>(null)
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null)

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
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
    if (preview.length > 500) preview = preview.slice(0, 500) + '…'
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

async function persistMessage(msg: ChatMessage) {
  try {
    await saveChatMessage(config.value, msg)
  } catch {
    historyBanner.value = t('chat.historySaveFailed')
  }
}

async function addUserMessage(content: string) {
  const msg: ChatMessage = {
    id: uid(),
    role: 'user',
    content,
    timestamp: new Date(),
  }
  messages.value.push(msg)
  await persistMessage(msg)
}

async function addAssistantMessage(response: QueryResponse) {
  const msg: ChatMessage = {
    id: uid(),
    role: 'assistant',
    content: response.message || t('chat.emptyResponse'),
    timestamp: new Date(),
    response,
  }
  messages.value.push(msg)
  appendEventLog(response)
  await persistMessage(msg)
}

async function addErrorMessage(content: string, retryable = true) {
  const msg: ChatMessage = {
    id: uid(),
    role: 'error',
    content,
    timestamp: new Date(),
  }
  messages.value.push(msg)
  await persistMessage(msg)
  return retryable
}

async function hydrateHistory() {
  historyBanner.value = null
  if (!config.value.workshopId.trim()) {
    messages.value = []
    return
  }

  try {
    messages.value = await loadChatHistory(config.value)
  } catch {
    historyBanner.value = t('chat.historyLoadFailed')
  }
}

async function executeTextQuery(query: string) {
  if (loading.value) return

  lastQuery.value = query
  await addUserMessage(query)
  loading.value = true

  const result = await apiExecuteTextQuery(config.value, query)

  if (!result.ok) {
    const message = formatApiError(result.error, t, 'errors.requestFailed')
    await addErrorMessage(message, result.error.retryable)
  } else {
    await addAssistantMessage(result.data)
  }

  loading.value = false
}

async function executeVoiceQuery(blob: Blob) {
  if (loading.value) return

  await addUserMessage(t('chat.voiceSubmitted'))
  loading.value = true

  const result = await apiExecuteVoiceQuery(config.value, blob)

  if (!result.ok) {
    const message = formatApiError(result.error, t, 'errors.voiceFailed')
    await addErrorMessage(message, result.error.retryable)
  } else {
    lastQuery.value = result.data.transcript ?? lastQuery.value
    await addAssistantMessage(result.data)
  }

  loading.value = false
}

async function onMicError(message: string) {
  await addErrorMessage(message, false)
}

async function onRetry() {
  if (lastQuery.value) {
    await executeTextQuery(lastQuery.value)
  }
}

async function onClearHistory() {
  try {
    await clearChatHistory(config.value)
    messages.value = []
    historyBanner.value = t('settings.historyCleared')
  } catch {
    historyBanner.value = t('chat.historySaveFailed')
  }
}

function onChipClick(query: string) {
  chatPanelRef.value?.submitQuery(query)
}

function onLocaleChange(locale: AppConfig['locale']) {
  setAppLocale(locale)
  config.value = { ...config.value, locale }
}

watch(
  () => config.value.workshopId,
  () => {
    hydrateHistory()
  },
)

onMounted(() => {
  hydrateHistory()
})
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden bg-zinc-950">
    <header class="flex shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-5 py-2.5 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <div class="h-2 w-2 rounded-full bg-sky-500" />
        <h1 class="text-sm font-semibold tracking-tight text-zinc-100">
          {{ t('header.title') }}
        </h1>
        <span class="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
          {{ t('common.version') }}
        </span>
      </div>
      <ControlSettings
        :config="config"
        @update:config="config = $event"
        @locale-change="onLocaleChange"
        @clear-history="onClearHistory"
      />
    </header>

    <div
      v-if="historyBanner"
      class="shrink-0 border-b border-amber-800/40 bg-amber-950/30 px-5 py-2 text-xs text-amber-200"
    >
      {{ historyBanner }}
    </div>

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
          @retry="onRetry"
          @mic-error="onMicError"
        />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Send,
  Mic,
  MicOff,
  Loader2,
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  RotateCcw,
} from 'lucide-vue-next'
import type { AppConfig, ChatMessage } from '../types/api'
import MarkdownContent from './MarkdownContent.vue'
import RawJsonViewer from './RawJsonViewer.vue'
import ChatTypingIndicator from './ChatTypingIndicator.vue'
import { shouldShowChart } from '../utils/chartData'

const ResultChart = defineAsyncComponent(() => import('./ResultChart.vue'))

const props = defineProps<{
  config: AppConfig
  messages: ChatMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  submit: [query: string]
  'voice-submit': [blob: Blob]
  retry: []
  'mic-error': [message: string]
}>()

const { t, locale } = useI18n()

const inputText = ref('')
const messagesEndRef = ref<HTMLElement | null>(null)
const isRecording = ref(false)
const expandedIds = ref<Set<string>>(new Set())

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

function responseWrapper(msg: ChatMessage): Record<string, unknown> | null {
  if (!msg.response) return null
  const r = msg.response
  return {
    intent: r.intent,
    tool_name: r.tool_name,
    result: r.result,
    metadata: r.metadata,
  }
}

function hasChartableResult(msg: ChatMessage): boolean {
  return msg.role === 'assistant' && shouldShowChart(msg.response?.result ?? null)
}

function toggleAccordion(id: string) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedIds.value = next
}

function isExpanded(id: string) {
  return expandedIds.value.has(id)
}

function roleLabel(role: ChatMessage['role']) {
  if (role === 'user') return t('chat.roleYou')
  if (role === 'error') return t('chat.roleError')
  return t('chat.roleAi')
}

function formatTime(date: Date) {
  return date.toLocaleTimeString(locale.value, {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
  })
}

function handleSubmit() {
  const q = inputText.value.trim()
  if (!q || props.loading) return
  emit('submit', q)
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []

    const mimeType = MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : MediaRecorder.isTypeSupported('audio/wav')
        ? 'audio/wav'
        : ''

    mediaRecorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream)

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop())
      const blob = new Blob(audioChunks, {
        type: mediaRecorder?.mimeType || 'audio/webm',
      })
      if (blob.size > 0) emit('voice-submit', blob)
      mediaRecorder = null
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch {
    isRecording.value = false
    emit('mic-error', t('chat.micDenied'))
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
}

const canSubmit = computed(() => inputText.value.trim().length > 0 && !props.loading)

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
  },
)

defineExpose({
  setInput(value: string) {
    inputText.value = value
  },
  submitQuery(query: string) {
    inputText.value = query
    handleSubmit()
  },
})
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="relative shrink-0 border-b border-zinc-800 px-4 py-3">
      <div
        v-if="loading"
        class="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-zinc-800"
      >
        <div class="h-full w-1/3 animate-[shimmer_1.2s_ease-in-out_infinite] bg-sky-500/80" />
      </div>
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-950/60 ring-1 ring-sky-800/40">
          <Bot class="h-4 w-4 text-sky-400" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-zinc-100">{{ t('chat.title') }}</h2>
          <p class="text-[10px] text-zinc-500">{{ t('chat.subtitle') }}</p>
        </div>
      </div>
    </div>

    <div
      class="min-h-0 flex-1 overflow-y-auto px-4 py-4"
      :aria-busy="loading"
    >
      <div
        v-if="messages.length === 0 && !loading"
        class="flex h-full flex-col items-center justify-center text-center"
      >
        <Bot class="mb-3 h-10 w-10 text-zinc-700" />
        <p class="text-sm text-zinc-500">{{ t('chat.emptyTitle') }}</p>
        <p class="mt-1 text-xs text-zinc-600">{{ t('chat.emptyHint') }}</p>
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[92%] rounded-xl px-3.5 py-2.5"
            :class="
              msg.role === 'user'
                ? 'bg-sky-700/80 text-white'
                : msg.role === 'error'
                  ? 'border border-red-800/60 bg-red-950/30 text-red-300'
                  : 'border border-zinc-700/80 bg-zinc-900/80 text-zinc-200'
            "
          >
            <div class="mb-1.5 flex items-center gap-1.5">
              <component
                :is="msg.role === 'error' ? AlertCircle : msg.role === 'user' ? User : Bot"
                class="h-3 w-3 opacity-60"
              />
              <span class="text-[10px] font-medium uppercase tracking-wider opacity-60">
                {{ roleLabel(msg.role) }}
              </span>
              <time class="ml-auto text-[10px] opacity-40">{{ formatTime(msg.timestamp) }}</time>
            </div>

            <MarkdownContent
              v-if="msg.role === 'assistant'"
              :content="msg.content"
            />
            <p v-else class="text-sm leading-relaxed">{{ msg.content }}</p>

            <button
              v-if="msg.role === 'error'"
              type="button"
              class="mt-2 flex items-center gap-1.5 rounded-md border border-red-700/50 px-2 py-1 text-xs text-red-200 transition-colors hover:bg-red-900/30"
              @click="emit('retry')"
            >
              <RotateCcw class="h-3 w-3" />
              {{ t('common.retry') }}
            </button>

            <div
              v-if="msg.role === 'assistant' && (hasChartableResult(msg) || responseWrapper(msg))"
              class="mt-3 border-t border-zinc-700/60 pt-3"
            >
              <ResultChart
                v-if="hasChartableResult(msg)"
                :result="msg.response!.result"
              />

              <button
                v-if="responseWrapper(msg)"
                type="button"
                class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200"
                @click="toggleAccordion(msg.id)"
              >
                <component
                  :is="isExpanded(msg.id) ? ChevronDown : ChevronRight"
                  class="h-3.5 w-3.5 shrink-0"
                />
                <span>{{ t('chat.inspectData') }}</span>
              </button>
              <div v-show="isExpanded(msg.id) && responseWrapper(msg)" class="mt-2">
                <RawJsonViewer :data="responseWrapper(msg)!" />
              </div>
            </div>
          </div>
        </div>

        <ChatTypingIndicator v-if="loading" :show-shimmer="false" />
      </div>
      <div ref="messagesEndRef" />
    </div>

    <div class="shrink-0 border-t border-zinc-800 bg-zinc-900/40 px-4 py-3">
      <div class="flex items-end gap-2">
        <div class="relative min-w-0 flex-1">
          <textarea
            v-model="inputText"
            rows="2"
            :placeholder="t('chat.placeholder')"
            class="w-full resize-none rounded-xl border border-zinc-700 bg-zinc-950 px-3.5 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
            :disabled="loading"
            @keydown="handleKeydown"
          />
        </div>

        <div class="flex shrink-0 flex-col gap-1.5">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg border transition-colors"
            :class="
              isRecording
                ? 'border-red-600 bg-red-950/50 text-red-400 animate-pulse'
                : 'border-zinc-700 bg-zinc-800 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'
            "
            :disabled="loading"
            :title="isRecording ? t('chat.stopRecording') : t('chat.recordVoice')"
            @click="toggleRecording"
          >
            <MicOff v-if="isRecording" class="h-4 w-4" />
            <Mic v-else class="h-4 w-4" />
          </button>

          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            :class="canSubmit ? 'bg-sky-600 text-white hover:bg-sky-500' : 'bg-zinc-800 text-zinc-600'"
            :disabled="!canSubmit"
            :title="t('chat.send')"
            @click="handleSubmit"
          >
            <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
            <Send v-else class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(400%);
  }
}
</style>

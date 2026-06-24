<script setup lang="ts">
import { ref, computed, watch, nextTick, defineAsyncComponent } from 'vue'
import { Send, Mic, MicOff, Loader2, Bot, User } from 'lucide-vue-next'
import type { AppConfig, ChatMessage } from '../types/api'
import MarkdownContent from './MarkdownContent.vue'
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
  'set-input': [query: string]
}>()

const inputText = ref('')
const messagesEndRef = ref<HTMLElement | null>(null)
const isRecording = ref(false)

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

function hasChartableResult(msg: ChatMessage): boolean {
  return msg.role === 'assistant' && shouldShowChart(msg.response?.result ?? null)
}

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', {
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
      stream.getTracks().forEach((t) => t.stop())
      const blob = new Blob(audioChunks, {
        type: mediaRecorder?.mimeType || 'audio/webm',
      })
      if (blob.size > 0) {
        emit('voice-submit', blob)
      }
      mediaRecorder = null
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch (err) {
    console.error('Microphone access failed:', err)
    isRecording.value = false
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
  () => props.messages.length,
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
    <!-- Chat header -->
    <div class="shrink-0 border-b border-zinc-800 px-4 py-3">
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-950/60 ring-1 ring-sky-800/40">
          <Bot class="h-4 w-4 text-sky-400" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-zinc-100">MES AI Assistant</h2>
          <p class="text-[10px] text-zinc-500">Query console</p>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
      <div
        v-if="messages.length === 0"
        class="flex h-full flex-col items-center justify-center text-center"
      >
        <Bot class="mb-3 h-10 w-10 text-zinc-700" />
        <p class="text-sm text-zinc-500">Start a conversation</p>
        <p class="mt-1 text-xs text-zinc-600">Type a query or use quick-test chips</p>
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
            <!-- Role label -->
            <div class="mb-1.5 flex items-center gap-1.5">
              <component
                :is="msg.role === 'user' ? User : Bot"
                class="h-3 w-3 opacity-60"
              />
              <span class="text-[10px] font-medium uppercase tracking-wider opacity-60">
                {{ msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'AI' }}
              </span>
              <time class="ml-auto text-[10px] opacity-40">{{ formatTime(msg.timestamp) }}</time>
            </div>

            <!-- Markdown report (two-pass synthesis from backend) -->
            <MarkdownContent
              v-if="msg.role === 'assistant'"
              :content="msg.content"
            />
            <p v-else class="text-sm leading-relaxed">{{ msg.content }}</p>

            <!-- Optional chart when result data supports visualization -->
            <div
              v-if="msg.role === 'assistant' && hasChartableResult(msg)"
              class="mt-3 border-t border-zinc-700/60 pt-3"
            >
              <ResultChart :result="msg.response!.result" />
            </div>
          </div>
        </div>
      </div>
      <div ref="messagesEndRef" />
    </div>

    <!-- Input area -->
    <div class="shrink-0 border-t border-zinc-800 bg-zinc-900/40 px-4 py-3">
      <div class="flex items-end gap-2">
        <div class="relative min-w-0 flex-1">
          <textarea
            v-model="inputText"
            rows="2"
            placeholder="Ask about yield, equipment, inventory…"
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
            :title="isRecording ? 'Stop recording' : 'Record voice query'"
            @click="toggleRecording"
          >
            <MicOff v-if="isRecording" class="h-4 w-4" />
            <Mic v-else class="h-4 w-4" />
          </button>

          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            :class="
              canSubmit
                ? 'bg-sky-600 text-white hover:bg-sky-500'
                : 'bg-zinc-800 text-zinc-600'
            "
            :disabled="!canSubmit"
            title="Send query"
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

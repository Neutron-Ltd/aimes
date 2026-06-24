<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Activity, Database, Zap } from 'lucide-vue-next'
import type { AppConfig, EventLogEntry, HealthStatus, QuickChip } from '../types/api'
import { QUICK_CHIPS } from '../types/api'
import type { HealthResponse } from '../types/api'

const props = defineProps<{
  config: AppConfig
  eventLog: EventLogEntry[]
}>()

const emit = defineEmits<{
  'chip-click': [query: string]
}>()

const healthStatus = ref<HealthStatus>('checking')
const healthDetail = ref<string>('')
let pollTimer: ReturnType<typeof setInterval> | null = null

function buildHeaders(): HeadersInit {
  const headers: HeadersInit = {}
  if (props.config.workshopId.trim()) {
    headers['X-MES-Workshop-Id'] = props.config.workshopId.trim()
  }
  return headers
}

async function checkHealth() {
  healthStatus.value = 'checking'
  const base = props.config.baseURL.replace(/\/$/, '')

  try {
    const res = await fetch(`${base}/api/v1/health`, {
      method: 'GET',
      headers: buildHeaders(),
    })

    if (!res.ok) {
      healthStatus.value = 'unhealthy'
      healthDetail.value = `HTTP ${res.status}`
      return
    }

    const data = (await res.json()) as HealthResponse
    healthStatus.value = 'healthy'
    healthDetail.value = data.status ?? 'ok'
  } catch (err) {
    healthStatus.value = 'unhealthy'
    const msg = err instanceof Error ? err.message : 'Connection failed'
    healthDetail.value =
      msg === 'Failed to fetch'
        ? 'Blocked by browser (CORS) or backend unreachable'
        : msg
  }
}

function onChipClick(chip: QuickChip) {
  emit('chip-click', chip.query)
}

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

onMounted(() => {
  checkHealth()
  pollTimer = setInterval(checkHealth, 10_000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <div class="shrink-0 border-b border-zinc-800 px-5 py-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-800">
            <Activity class="h-4 w-4 text-sky-400" />
          </div>
          <div>
            <h2 class="text-sm font-semibold text-zinc-100">Dashboard Simulation</h2>
            <p class="text-[11px] text-zinc-500">MES control station monitor</p>
          </div>
        </div>

        <!-- Health indicator -->
        <div class="flex items-center gap-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2">
          <span
            class="relative flex h-2.5 w-2.5"
            :title="healthDetail"
          >
            <span
              v-if="healthStatus === 'healthy'"
              class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-40"
            />
            <span
              class="relative inline-flex h-2.5 w-2.5 rounded-full"
              :class="{
                'bg-emerald-500': healthStatus === 'healthy',
                'bg-red-500': healthStatus === 'unhealthy',
                'bg-amber-500 animate-pulse': healthStatus === 'checking',
              }"
            />
          </span>
          <div class="text-right">
            <p class="text-[11px] font-medium text-zinc-300">
              {{ healthStatus === 'healthy' ? 'Online' : healthStatus === 'unhealthy' ? 'Offline' : 'Checking…' }}
            </p>
            <p class="font-mono text-[10px] text-zinc-500">{{ healthDetail }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick-click chips -->
    <div class="shrink-0 border-b border-zinc-800 px-5 py-4">
      <div class="mb-2.5 flex items-center gap-2">
        <Zap class="h-3.5 w-3.5 text-amber-400" />
        <span class="text-xs font-medium uppercase tracking-wider text-zinc-500">Quick Test Prompts</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="chip in QUICK_CHIPS"
          :key="chip.id"
          type="button"
          class="group rounded-lg border border-zinc-700/80 bg-zinc-800/40 px-3 py-2 text-left transition-all hover:border-sky-600/50 hover:bg-zinc-800"
          @click="onChipClick(chip)"
        >
          <span class="block text-xs font-medium text-zinc-200 group-hover:text-sky-300">
            {{ chip.label }}
          </span>
          <span class="mt-0.5 block max-w-xs truncate font-mono text-[10px] text-zinc-500">
            {{ chip.query }}
          </span>
        </button>
      </div>
    </div>

    <!-- Event log -->
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div class="flex shrink-0 items-center gap-2 border-b border-zinc-800/60 px-5 py-3">
        <Database class="h-3.5 w-3.5 text-emerald-400" />
        <span class="text-xs font-medium uppercase tracking-wider text-zinc-500">
          Execution Event Log
        </span>
        <span class="ml-auto rounded-full bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-400">
          {{ eventLog.length }} events
        </span>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto px-5 py-3">
        <div
          v-if="eventLog.length === 0"
          class="flex h-full flex-col items-center justify-center text-center"
        >
          <Database class="mb-3 h-8 w-8 text-zinc-700" />
          <p class="text-sm text-zinc-500">No execution events yet</p>
          <p class="mt-1 max-w-xs text-xs text-zinc-600">
            Structured <code class="text-zinc-500">result</code> payloads from the backend will appear here
          </p>
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="entry in [...eventLog].reverse()"
            :key="entry.id"
            class="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3"
          >
            <div class="mb-2 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-sky-400">
                  {{ entry.intent }}
                </span>
                <span class="font-mono text-[10px] text-zinc-500">{{ entry.toolName }}</span>
              </div>
              <time class="font-mono text-[10px] text-zinc-600">{{ formatTime(entry.timestamp) }}</time>
            </div>

            <div v-if="entry.schemaTables.length" class="mb-2 flex flex-wrap gap-1">
              <span
                v-for="table in entry.schemaTables"
                :key="table"
                class="rounded border border-emerald-800/40 bg-emerald-950/30 px-1.5 py-0.5 font-mono text-[10px] text-emerald-400"
              >
                {{ table }}
              </span>
            </div>

            <pre class="max-h-24 overflow-auto font-mono text-[10px] leading-relaxed text-zinc-500">{{ entry.resultPreview }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

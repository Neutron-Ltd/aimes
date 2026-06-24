<script setup lang="ts">
import { ref } from 'vue'
import { Settings, X } from 'lucide-vue-next'
import type { AppConfig } from '../types/api'

const props = defineProps<{
  config: AppConfig
}>()

const emit = defineEmits<{
  'update:config': [config: AppConfig]
}>()

const open = ref(false)

function updateField<K extends keyof AppConfig>(key: K, value: AppConfig[K]) {
  emit('update:config', { ...props.config, [key]: value })
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      class="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800/80 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-zinc-100"
      @click="open = !open"
    >
      <Settings class="h-3.5 w-3.5" />
      <span>Control Settings</span>
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="open"
        class="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-zinc-700 bg-zinc-900 p-4 shadow-2xl shadow-black/50"
      >
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-zinc-100">API Configuration</h3>
          <button
            type="button"
            class="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
            @click="open = false"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="mb-1.5 block text-xs font-medium text-zinc-400">Base URL</label>
            <input
              :value="config.baseURL"
              type="url"
              placeholder="(empty = same host, e.g. Docker/nginx)"
              class="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
              @input="updateField('baseURL', ($event.target as HTMLInputElement).value)"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-xs font-medium text-zinc-400">
              X-MES-Workshop-Id
            </label>
            <input
              :value="config.workshopId"
              type="text"
              placeholder="YOUR_DATA_AUTH"
              class="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
              @input="updateField('workshopId', ($event.target as HTMLInputElement).value)"
            />
          </div>

          <div class="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950/50 px-3 py-2.5">
            <div>
              <p class="text-xs font-medium text-zinc-300">enrich_response</p>
              <p class="text-[10px] text-zinc-500">Include RAG enrichment in response</p>
            </div>
            <button
              type="button"
              role="switch"
              :aria-checked="config.enrichResponse"
              class="relative h-5 w-9 shrink-0 rounded-full transition-colors"
              :class="config.enrichResponse ? 'bg-emerald-600' : 'bg-zinc-700'"
              @click="updateField('enrichResponse', !config.enrichResponse)"
            >
              <span
                class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform"
                :class="config.enrichResponse ? 'left-[18px]' : 'left-0.5'"
              />
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

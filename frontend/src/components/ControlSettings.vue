<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Settings, X } from 'lucide-vue-next'
import type { AppConfig } from '../types/api'
import type { AppLocale } from '../i18n'

const props = defineProps<{
  config: AppConfig
}>()

const emit = defineEmits<{
  'update:config': [config: AppConfig]
  'locale-change': [locale: AppLocale]
  'clear-history': []
}>()

const { t } = useI18n()
const open = ref(false)

function updateField<K extends keyof AppConfig>(key: K, value: AppConfig[K]) {
  emit('update:config', { ...props.config, [key]: value })
}

function setLocale(locale: AppLocale) {
  updateField('locale', locale)
  emit('locale-change', locale)
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
      <span>{{ t('settings.title') }}</span>
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
          <h3 class="text-sm font-semibold text-zinc-100">{{ t('settings.apiConfig') }}</h3>
          <button
            type="button"
            class="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
            @click="open = false"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <div
          v-if="!config.workshopId.trim()"
          class="mb-4 rounded-lg border border-amber-800/40 bg-amber-950/20 px-3 py-2 text-[11px] text-amber-200"
        >
          {{ t('settings.historyWarning') }}
        </div>

        <div class="space-y-4">
          <div>
            <label class="mb-1.5 block text-xs font-medium text-zinc-400">{{ t('settings.language') }}</label>
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors"
                :class="
                  config.locale === 'zh-CN'
                    ? 'border-sky-600 bg-sky-950/40 text-sky-300'
                    : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:border-zinc-600'
                "
                @click="setLocale('zh-CN')"
              >
                中文
              </button>
              <button
                type="button"
                class="flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors"
                :class="
                  config.locale === 'en-US'
                    ? 'border-sky-600 bg-sky-950/40 text-sky-300'
                    : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:border-zinc-600'
                "
                @click="setLocale('en-US')"
              >
                English
              </button>
            </div>
          </div>

          <div>
            <label class="mb-1.5 block text-xs font-medium text-zinc-400">{{ t('settings.baseUrl') }}</label>
            <input
              :value="config.baseURL"
              type="url"
              placeholder="http://127.0.0.1:8000"
              class="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
              @input="updateField('baseURL', ($event.target as HTMLInputElement).value)"
            />
          </div>

          <div>
            <label class="mb-1.5 block text-xs font-medium text-zinc-400">{{ t('settings.workshopId') }}</label>
            <input
              :value="config.workshopId"
              type="text"
              :placeholder="t('settings.workshopIdPlaceholder')"
              class="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-sky-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
              @input="updateField('workshopId', ($event.target as HTMLInputElement).value)"
            />
          </div>

          <div class="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950/50 px-3 py-2.5">
            <div>
              <p class="text-xs font-medium text-zinc-300">{{ t('settings.enrichResponse') }}</p>
              <p class="text-[10px] text-zinc-500">{{ t('settings.enrichResponseHint') }}</p>
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

          <button
            type="button"
            class="w-full rounded-lg border border-red-800/50 bg-red-950/20 px-3 py-2 text-xs font-medium text-red-300 transition-colors hover:bg-red-950/40 disabled:opacity-40"
            :disabled="!config.workshopId.trim()"
            @click="emit('clear-history')"
          >
            {{ t('settings.clearHistory') }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

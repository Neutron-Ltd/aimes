<script setup lang="ts">
import { Bot } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

defineProps<{
  showShimmer?: boolean
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex justify-start">
    <div
      class="max-w-[92%] rounded-xl border border-zinc-700/80 bg-zinc-900/80 px-3.5 py-3"
      role="status"
      aria-live="polite"
    >
      <div
        v-if="showShimmer"
        class="mb-2 h-0.5 w-full overflow-hidden rounded-full bg-zinc-800"
      >
        <div class="h-full w-1/3 animate-[shimmer_1.2s_ease-in-out_infinite] rounded-full bg-sky-500/70" />
      </div>

      <div class="mb-2 flex items-center gap-1.5">
        <Bot class="h-3 w-3 text-sky-400/70" />
        <span class="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
          {{ t('chat.roleAi') }}
        </span>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-sm text-zinc-400">{{ t('chat.analyzing') }}</span>
        <span class="flex gap-1">
          <span
            class="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-400"
            style="animation-delay: 0ms"
          />
          <span
            class="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-400"
            style="animation-delay: 150ms"
          />
          <span
            class="h-1.5 w-1.5 animate-bounce rounded-full bg-sky-400"
            style="animation-delay: 300ms"
          />
        </span>
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

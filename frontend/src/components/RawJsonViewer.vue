<script setup lang="ts">
import { computed } from 'vue'
import { Copy, Check } from 'lucide-vue-next'
import { ref } from 'vue'

const props = defineProps<{
  data: unknown
}>()

const copied = ref(false)

const formatted = computed(() => {
  try {
    return JSON.stringify(props.data, null, 2)
  } catch {
    return String(props.data)
  }
})

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(formatted.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    /* clipboard unavailable */
  }
}
</script>

<template>
  <div class="relative rounded-lg border border-zinc-700/80 bg-zinc-950/80">
    <button
      type="button"
      class="absolute right-2 top-2 rounded p-1 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-300"
      title="Copy JSON"
      @click="copyToClipboard"
    >
      <Check v-if="copied" class="h-3.5 w-3.5 text-emerald-400" />
      <Copy v-else class="h-3.5 w-3.5" />
    </button>
    <pre class="max-h-64 overflow-auto p-3 pr-10 font-mono text-[11px] leading-relaxed text-emerald-300/90">{{ formatted }}</pre>
  </div>
</template>

<template>
  <el-header class="header">
    <div class="header-layout">
      <div class="header-left">
        <button
          v-if="showBackHome"
          type="button"
          class="header-back-btn"
          @click="goHome"
        >
          <el-icon><ArrowLeft /></el-icon>
          <span>{{ t('common.backHome') }}</span>
        </button>
        <div class="date-info">
          <div class="weekday">{{ weekday }}</div>
          <div class="date">{{ dateText }}</div>
        </div>
      </div>

      <div class="header-title">
        <div class="title-badge">
          <span class="title-dot title-dot--left"></span>
          <div class="title-core">
            <span class="title-line title-line--top"></span>
            <h1>{{ title }}</h1>
            <span class="title-line title-line--bottom"></span>
            <span class="title-indicator title-indicator--left"></span>
            <span class="title-indicator title-indicator--right"></span>
            <span class="title-dataflow"></span>
          </div>
          <span class="title-dot title-dot--right"></span>
        </div>
      </div>

      <div class="header-right">
        

        <div class="lang-switch" role="group" aria-label="Language">
          <button
            type="button"
            class="lang-btn"
            :class="{ 'lang-btn--active': locale === 'zh' }"
            @click="setLocale('zh')"
          >
            中文
          </button>
          <button
            type="button"
            class="lang-btn"
            :class="{ 'lang-btn--active': locale === 'en' }"
            @click="setLocale('en')"
          >
            EN
          </button>
        </div>
        <button
          type="button"
          class="header-fullscreen-btn"
          :title="isFullscreen ? t('common.exitFullscreen') : t('common.fullscreen')"
          :aria-label="isFullscreen ? t('common.exitFullscreen') : t('common.fullscreen')"
          @click="toggleFullscreen"
        >
          <el-icon>
            <ScaleToOriginal v-if="isFullscreen" />
            <FullScreen v-else />
          </el-icon>
        </button>
      </div>
    </div>
  </el-header>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FullScreen, ScaleToOriginal } from '@element-plus/icons-vue'
import { useLocale } from '../composables/useLocale'

const route = useRoute()
const router = useRouter()
const { locale, setLocale, title, weekdays, formatDateTime, t } = useLocale()

const showBackHome = computed(() => route.path.startsWith('/assistant/'))

function goHome() {
  router.push('/')
}

const weekday = ref('')
const dateText = ref('')
const isFullscreen = ref(false)

function getFullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement
}

function syncFullscreenState() {
  isFullscreen.value = Boolean(getFullscreenElement())
}

async function toggleFullscreen() {
  try {
    if (getFullscreenElement()) {
      if (document.exitFullscreen) {
        await document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        await document.webkitExitFullscreen()
      }
    } else {
      const el = document.documentElement
      if (el.requestFullscreen) {
        await el.requestFullscreen()
      } else if (el.webkitRequestFullscreen) {
        await el.webkitRequestFullscreen()
      }
    }
  } catch {
    // 浏览器可能拦截全屏（未由用户手势触发等）
  }
}

function updateDateTime() {
  const now = new Date()
  weekday.value = weekdays.value[now.getDay()]
  dateText.value = formatDateTime(now)
}

let timer = null

watch(locale, () => {
  updateDateTime()
})

onMounted(() => {
  updateDateTime()
  timer = window.setInterval(updateDateTime, 1000)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  document.addEventListener('webkitfullscreenchange', syncFullscreenState)
  syncFullscreenState()
})

onUnmounted(() => {
  if (timer !== null) {
    clearInterval(timer)
  }
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  document.removeEventListener('webkitfullscreenchange', syncFullscreenState)
})
</script>

<style>
@import '../assets/styles/header.css';
</style>

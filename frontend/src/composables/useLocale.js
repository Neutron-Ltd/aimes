import { computed, ref } from 'vue'
import {
  assistantAccents,
  assistantAvatars,
  assistantKeys,
  assistantKpiValues,
  assistantLayouts,
  assistantRoutes,
  messages
} from '../i18n/messages'

const LOCALE_KEY = 'mes-ai-locale'

const locale = ref(
  typeof localStorage !== 'undefined' && localStorage.getItem(LOCALE_KEY) === 'en' ? 'en' : 'zh'
)

function applyDocumentLang(lang) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'
  }
}

applyDocumentLang(locale.value)

function getByPath(obj, path) {
  return path.split('.').reduce((acc, key) => acc?.[key], obj)
}

function interpolate(template, params = {}) {
  if (!template || typeof template !== 'string') return template
  return Object.keys(params).reduce(
    (str, key) => str.replaceAll(`{${key}}`, params[key]),
    template
  )
}

export function useLocale() {
  const setLocale = (lang) => {
    if (lang !== 'zh' && lang !== 'en') return
    locale.value = lang
    localStorage.setItem(LOCALE_KEY, lang)
    applyDocumentLang(lang)
  }

  const t = (key, params) => {
    const value = getByPath(messages[locale.value], key)
    if (value === undefined) return key
    if (typeof value === 'string') return interpolate(value, params)
    return value
  }

  const title = computed(() => messages[locale.value].header.title)
  const weekdays = computed(() => messages[locale.value].header.weekdays)

  const formatDateTime = (date) => {
    const pad2 = (v) => String(v).padStart(2, '0')
    const y = date.getFullYear()
    const m = pad2(date.getMonth() + 1)
    const d = pad2(date.getDate())
    const hh = pad2(date.getHours())
    const mm = pad2(date.getMinutes())
    const ss = pad2(date.getSeconds())

    if (locale.value === 'en') {
      return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
    }
    return `${y}年${m}月${d}日 ${hh}:${mm}:${ss}`
  }

  const homeAssistants = computed(() => {
    return assistantKeys.map((key) => {
      const text = messages[locale.value].assistants[key]
      return {
        key,
        title: text.title,
        avatar: assistantAvatars[key],
        route: assistantRoutes[key],
        details: text.homeDetails
      }
    })
  })

  const getAssistantPageConfig = (key) => {
    const text = messages[locale.value].assistants[key]
    const values = assistantKpiValues[key]
    return {
      title: text.title,
      subtitle: text.subtitle,
      avatar: assistantAvatars[key],
      accent: assistantAccents[key],
      layout: assistantLayouts[key],
      route: assistantRoutes[key],
      greeting: text.greeting,
      prompts: text.prompts,
      homeDetails: text.homeDetails,
      kpis: values.map((item, index) => ({
        ...item,
        label: text.kpiLabels[index]
      })),
      chartDefs: text.charts
    }
  }

  return {
    locale,
    setLocale,
    t,
    title,
    weekdays,
    formatDateTime,
    homeAssistants,
    getAssistantPageConfig
  }
}

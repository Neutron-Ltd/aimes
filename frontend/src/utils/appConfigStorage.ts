import type { AppLocale } from '../i18n'

const CONFIG_STORAGE_KEY = 'mesai-app-config'

export interface StoredAppConfig {
  baseURL?: string
  workshopId?: string
  enrichResponse?: boolean
  locale?: AppLocale
}

export function loadStoredConfig(): StoredAppConfig {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY)
    if (!raw) return {}
    return JSON.parse(raw) as StoredAppConfig
  } catch {
    return {}
  }
}

export function saveStoredConfig(config: StoredAppConfig) {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config))
}

export function defaultWorkshopId(): string {
  return import.meta.env.VITE_DEFAULT_WORKSHOP_ID ?? 'WS-001'
}

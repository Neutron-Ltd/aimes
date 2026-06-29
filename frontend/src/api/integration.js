/** Which assistant modules use live backend integration. */

const integrated = (import.meta.env.VITE_INTEGRATED_ASSISTANTS ?? 'production')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)

export function isAssistantIntegrated(assistantKey) {
  return integrated.includes(assistantKey)
}

export function listIntegratedAssistants() {
  return [...integrated]
}

/** Map app locale keys to backend locale codes. */

export function toApiLocale(appLocale) {
  return appLocale === 'en' ? 'en-US' : 'zh-CN'
}

export function fromApiLocale(apiLocale) {
  return apiLocale === 'en-US' ? 'en' : 'zh'
}

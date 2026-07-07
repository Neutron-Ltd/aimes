import DOMPurify from 'dompurify'
import mermaid from 'mermaid'
import { marked } from 'marked'

let mermaidInitialized = false

marked.setOptions({
  breaks: true,
  gfm: true
})

marked.use({
  renderer: {
    code({ text, lang }) {
      if (lang === 'mermaid') {
        return `<div class="mermaid chat-mermaid">${text}</div>`
      }
      const language = lang ? ` class="language-${lang}"` : ''
      const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
      return `<pre><code${language}>${escaped}</code></pre>`
    }
  }
})

function ensureMermaidInitialized() {
  if (mermaidInitialized) return
  mermaid.initialize({
    startOnLoad: false,
    theme: 'neutral',
    securityLevel: 'strict'
  })
  mermaidInitialized = true
}

/**
 * Convert assistant Markdown to sanitized HTML for chat display.
 * @param {string} text
 * @returns {string}
 */
export function renderMarkdown(text) {
  if (!text) return ''
  const html = marked.parse(text, { async: false })
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['data-processed']
  })
}

/**
 * Render Mermaid diagrams inside a chat container after v-html update.
 * @param {HTMLElement | null | undefined} root
 */
export async function initMermaidIn(root) {
  if (!root) return
  ensureMermaidInitialized()
  const nodes = root.querySelectorAll('.mermaid:not([data-processed])')
  if (!nodes.length) return
  await mermaid.run({ nodes })
}

<template>
  <el-col
    :xs="24"
    :sm="24"
    :md="24"
    :lg="8"
    :xl="7"
    class="console-col"
    :class="{ 'console-col--collapsed': collapsed }"
  >
    <Transition name="console-panel">
      <el-card v-show="!collapsed" class="ai-console" shadow="never">
        <button
          type="button"
          class="console-collapse-btn"
          :title="t('common.chatHide')"
          :aria-label="t('common.chatHide')"
          @click="setCollapsed(true)"
        >
          <el-icon><DArrowRight /></el-icon>
        </button>

        <div class="console-intro" :class="{ 'console-intro--compact': hasConversation }">
          <div class="console-intro-avatar">
            <img :src="avatar" :alt="title" class="console-avatar" />
          </div>
          <div class="console-intro-content">
            <div class="chat-message assistant-message console-greeting">
              <strong>{{ title }}</strong>
              <span>{{ greeting }}</span>
            </div>
            <el-button
              v-for="prompt in prompts"
              v-show="showPrompts"
              :key="prompt"
              class="quick-prompt"
              text
              :disabled="thinking"
              @click="handlePromptClick(prompt)"
            >
              {{ prompt }}
            </el-button>
          </div>
        </div>
        <div v-show="!hasConversation" class="console-intro-spacer" aria-hidden="true"></div>

        <div v-show="hasConversation" ref="chatWindowRef" class="chat-window">
          <div class="chat-messages">
            <div
              v-for="message in messages"
              :key="message.id"
              class="chat-message"
              :class="`${message.role}-message`"
            >
              <strong v-if="message.role === 'assistant'">{{ title }}</strong>
              <div
                v-if="message.role === 'assistant'"
                class="chat-markdown"
                v-html="renderMarkdown(message.content)"
              />
              <span v-else>{{ message.content }}</span>
            </div>

            <div v-if="thinking" class="chat-message assistant-message thinking-message">
              <strong>{{ title }}</strong>
              <span class="thinking-text">{{ t('common.chatThinking') }}</span>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputValue"
            :placeholder="t('common.chatPlaceholder')"
            :disabled="thinking"
            @keyup.enter="handleSend"
          />
          <el-button type="primary" :loading="thinking" @click="handleSend">
            {{ t('common.send') }}
          </el-button>
        </div>
      </el-card>
    </Transition>

    <Teleport to="body">
      <Transition name="console-dock">
        <button
          v-if="collapsed"
          type="button"
          class="ai-console-dock"
          :style="{ '--assistant-accent': accent }"
          :title="t('common.chatShow')"
          :aria-label="t('common.chatShow')"
          @click="setCollapsed(false)"
        >
          <span class="ai-console-dock-avatar-wrap">
            <img
              :src="avatar"
              :alt="title"
              class="ai-console-dock-avatar"
              :style="dockAvatarStyle"
            />
            <span v-if="thinking" class="ai-console-dock-pulse" />
          </span>
          <span class="ai-console-dock-label">{{ t('common.aiAgent') }}</span>
          <el-icon class="ai-console-dock-icon"><DArrowLeft /></el-icon>
        </button>
      </Transition>
    </Teleport>
  </el-col>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { useAssistantChat } from '../composables/useAssistantChat'
import { useLocale } from '../composables/useLocale'
import { renderMarkdown } from '../utils/markdown'

const props = defineProps({
  /** 助手标识，对接后端时使用：production / warehouse / quality / equipment / procurement */
  assistantKey: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  greeting: {
    type: String,
    required: true
  },
  prompts: {
    type: Array,
    default: () => []
  },
  avatar: {
    type: String,
    required: true
  },
  accent: {
    type: String,
    default: '#38bdf8'
  }
})

const collapsed = defineModel('collapsed', { type: Boolean, default: false })

const emit = defineEmits(['send', 'prompt'])

const { t } = useLocale()
const { sendMessage, sendPrompt } = useAssistantChat(props.assistantKey)

const inputValue = ref('')
const thinking = ref(false)
const messages = ref([])
const chatWindowRef = ref(null)
let messageSeed = 0

const showPrompts = computed(() => messages.value.length === 0 && !thinking.value)
const hasConversation = computed(() => messages.value.length > 0 || thinking.value)

/** 各助手头像构图不同，微调悬浮窗裁剪焦点以露出头部 */
const dockAvatarFocus = {
  production: { objectPosition: 'center 6%', scale: 1.6 },
  warehouse: { objectPosition: 'center 4%', scale: 1.65 },
  quality: { objectPosition: 'center 8%', scale: 1.55 },
  equipment: { objectPosition: 'center 5%', scale: 1.6 },
  procurement: { objectPosition: 'center 7%', scale: 1.58 }
}

const dockAvatarStyle = computed(() => {
  const focus = dockAvatarFocus[props.assistantKey] ?? { objectPosition: 'top center', scale: 1.55 }
  return {
    objectPosition: focus.objectPosition,
    transform: `scale(${focus.scale})`,
    transformOrigin: 'top center'
  }
})

const storageKey = computed(() => `mes-ai-console-collapsed-${props.assistantKey}`)

onMounted(() => {
  if (typeof sessionStorage === 'undefined') return
  const stored = sessionStorage.getItem(storageKey.value)
  if (stored === '1') {
    collapsed.value = true
  }
})

watch(collapsed, (value) => {
  if (typeof sessionStorage === 'undefined') return
  sessionStorage.setItem(storageKey.value, value ? '1' : '0')
})

function setCollapsed(value) {
  collapsed.value = value
}

function createMessage(role, content) {
  messageSeed += 1
  return { id: `${Date.now()}-${messageSeed}`, role, content }
}

async function scrollToBottom() {
  await nextTick()
  const el = chatWindowRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

async function runConversation(userText, eventName) {
  const text = userText.trim()
  if (!text || thinking.value) return

  thinking.value = true
  messages.value.push(createMessage('user', text))
  await scrollToBottom()

  try {
    const reply = eventName === 'prompt' ? await sendPrompt(text) : await sendMessage(text)
    if (reply) {
      messages.value.push(createMessage('assistant', reply))
    }
    emit(eventName, text)
  } finally {
    thinking.value = false
    await scrollToBottom()
  }
}

function handleSend() {
  const message = inputValue.value.trim()
  if (!message) return

  inputValue.value = ''
  runConversation(message, 'send')
}

function handlePromptClick(prompt) {
  runConversation(prompt, 'prompt')
}
</script>

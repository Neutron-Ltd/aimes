<template>
  <section class="content">
    <el-row class="hero-section" :gutter="24" align="middle" justify="center">
      <el-col :xs="0" :md="4" :lg="3">
        <div class="hero-decoration left-decoration">
          <div class="dot-1"></div>
          <div class="dot-2"></div>
          <div class="dot-3"></div>
        </div>
      </el-col>

      <div class="hero-content">
        <h2>{{ t('home.heroTitle') }}</h2>
        <p class="subtitle">{{ t('home.heroSubtitle') }}</p>
        <div class="partners">
          <el-tag v-for="partner in partners" :key="partner.label" effect="dark" round class="partner-tag">
            <span class="partner-icon">{{ partner.icon }}</span>
            <span>{{ partner.label }}</span>
          </el-tag>
        </div>
      </div>

      <el-col :xs="0" :md="4" :lg="3">
        <div class="hero-decoration right-decoration">
          <div class="dot-1"></div>
          <div class="dot-2"></div>
          <div class="dot-3"></div>
        </div>
      </el-col>
    </el-row>

    <section class="cards-container">
      <el-row class="cards-wrapper" :gutter="24" justify="center" align="middle">
        <el-col
          v-for="(assistant, index) in assistants"
          :key="assistant.route"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
          :xl="4"
          class="card-col"
        >
          <div
            class="card-shell"
            @mouseenter="setActiveCard(index)"
            @mouseleave="clearActiveCard"
            @click="selectCard(index)"
          >
            <!-- 整体缩放容器：边框 + 内容 + 头像一体 -->
            <article class="assistant-card" :class="{ 'is-active': activeCard === index }">
              <div class="card-aura" aria-hidden="true"></div>
              <div class="card-inner">
                <div class="card-scanline" aria-hidden="true"></div>

                <header class="card-header">
                  <div class="title-chip">
                    <span class="title-chip-dot"></span>
                    <h3 class="card-title">{{ assistant.title }}</h3>
                  </div>
                </header>

                <div class="card-body">
                  <div class="avatar-orbit" aria-hidden="true"></div>
                  <div class="avatar-ring">
                    <div class="avatar-frame">
                      <img :src="assistant.avatar" :alt="assistant.title" class="avatar" />
                    </div>
                  </div>
                </div>

                <footer class="card-footer">
                  <div class="footer-mask">
                    <span class="footer-label">{{ t('common.aiAgent') }}</span>
                    <span class="footer-action">{{ t('common.clickEnter') }}</span>
                  </div>
                </footer>
              </div>
            </article>

            <transition name="detail-fade">
              <aside v-if="activeCard === index" class="detail-panel" @click.stop>
                <div class="detail-panel-inner">
                  <div
                    v-for="(item, idx) in assistant.details"
                    :key="idx"
                    class="detail-item"
                  >
                    <div class="detail-title">
                      <span class="detail-icon">▶</span>
                      {{ item.title }}
                    </div>
                    <p class="detail-desc">{{ item.desc }}</p>
                  </div>
                </div>
              </aside>
            </transition>
          </div>
        </el-col>
      </el-row>
    </section>

    <div class="floating-ai">
      <img
        src="https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=professional%20businesswoman%20portrait%20headshot%20confident%20asian%20female%20executive&image_size=square"
        alt="AI"
        class="floating-avatar"
      />
      <div class="floating-ring"></div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLocale } from '../composables/useLocale'

const activeCard = ref(null)
const router = useRouter()
const { homeAssistants, t } = useLocale()

const partners = computed(() => t('home.partners'))
const assistants = homeAssistants

const setActiveCard = (index) => {
  activeCard.value = index
}

const clearActiveCard = () => {
  activeCard.value = null
}

const selectCard = (index) => {
  router.push(assistants.value[index].route)
}
</script>

<style scoped>
/* ── 页面容器 ── */
.content {
  position: relative;
  z-index: 5;
  width: 100%;
  max-width: 100%;
  min-height: 100%;
  padding: 1.25rem clamp(1rem, 3vw, 2.5rem) 2.25rem;
  overflow-x: hidden;
}

/* ── Hero 区 ── */
.hero-section {
  width: 100%;
  margin-bottom: 1.5rem;
}

.hero-content {
  width: 100%;
  max-width: min(61.25rem, 100%);
  margin: 0 auto;
  text-align: center;
  padding: 0 clamp(0.5rem, 2vw, 1rem);
}

.hero-content h2 {
  font-size: clamp(1.25rem, 2.8vw, 1.75rem);
  margin: 0 0 0.625rem;
  background: linear-gradient(90deg, #38bdf8, #a78bfa, #38bdf8);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: textGradient 4s linear infinite;
  text-shadow: none;
  filter: drop-shadow(0 0 18px rgba(59, 130, 246, 0.35));
}

.subtitle {
  font-size: clamp(0.8125rem, 1.6vw, 0.875rem);
  color: #94a3b8;
  max-width: min(56.25rem, 100%);
  line-height: 1.7;
  margin: 0 auto 1.25rem;
}

.partners {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.partners :deep(.partner-tag.el-tag) {
  --el-tag-bg-color: rgba(15, 23, 42, 0.65);
  --el-tag-border-color: rgba(59, 130, 246, 0.35);
  --el-tag-text-color: #c7d2fe;
  padding: 0.4375rem 0.875rem;
  font-size: 0.8125rem;
  backdrop-filter: blur(10px);
}

.partner-icon {
  margin-right: 0.375rem;
  font-size: 1rem;
}

.hero-decoration {
  flex: 0 0 7.5rem;
  height: 12.5rem;
  position: relative;
}

.left-decoration::before,
.right-decoration::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 6.25rem;
  height: 6.25rem;
  transform: translate(-50%, -50%);
  border: 2px solid;
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
}

.left-decoration::before {
  border-image: linear-gradient(135deg, #06b6d4, #3b82f6, #8b5cf6) 1;
  animation: rotateHex 8s linear infinite;
}

.right-decoration::before {
  border-image: linear-gradient(225deg, #06b6d4, #3b82f6, #8b5cf6) 1;
  animation: rotateHexReverse 8s linear infinite;
}

.left-decoration .dot-1,
.left-decoration .dot-2,
.left-decoration .dot-3,
.right-decoration .dot-1,
.right-decoration .dot-2,
.right-decoration .dot-3 {
  position: absolute;
  width: 0.5rem;
  height: 0.5rem;
  background: linear-gradient(135deg, #06b6d4, #a78bfa);
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.6);
  animation: dotFloat 3s ease-in-out infinite;
}

.left-decoration .dot-1 { top: 10px; left: 20px; }
.left-decoration .dot-2 { top: 40px; right: 10px; animation-delay: 0.7s; }
.left-decoration .dot-3 { bottom: 20px; left: 30px; animation-delay: 1.4s; }
.right-decoration .dot-1 { top: 10px; right: 20px; animation-delay: 0.2s; }
.right-decoration .dot-2 { top: 40px; left: 10px; animation-delay: 0.9s; }
.right-decoration .dot-3 { bottom: 20px; right: 30px; animation-delay: 1.6s; }

/* ── 卡片区 ── */
.cards-container {
  width: 100%;
  max-width: min(100rem, 100%);
  margin: 0 auto;
  overflow: visible;
}

.cards-wrapper {
  width: 100%;
  padding: 1rem 0 2.5rem;
  overflow: visible;
  align-items: stretch !important;
}

.cards-wrapper :deep(.el-col) {
  overflow: visible;
  display: flex;
  align-items: stretch;
}

.card-col {
  display: flex;
  justify-content: center;
  align-items: stretch;
  margin-bottom: 1.75rem;
  overflow: visible;
}

.card-shell {
  position: relative;
  width: 100%;
  max-width: min(17.5rem, 92vw);
  height: 100%;
  cursor: pointer;
  z-index: 1;
  overflow: visible;
  display: flex;
  flex-direction: column;
}

.card-shell:hover,
.card-shell:focus-within {
  z-index: 30;
}

/* ★ 核心：单一容器整体缩放，边框与内容同步 */
.assistant-card {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  flex: 1 1 auto;
  padding: 1.5px;
  border-radius: 1.75rem 1.75rem 2.25rem 1.25rem;
  background: linear-gradient(145deg, #38bdf8 0%, #6366f1 45%, #a78bfa 100%);
  box-shadow:
    0 0.5rem 2rem rgba(15, 23, 42, 0.45),
    0 0 1.5rem rgba(56, 189, 248, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  transform-origin: center center;
  transform: translateY(0) scale(1);
  transition:
    transform 0.38s cubic-bezier(0.34, 1.45, 0.64, 1),
    box-shadow 0.38s ease,
    filter 0.38s ease;
  will-change: transform;
  clip-path: polygon(
    0% 4%, 4% 0%, 96% 0%, 100% 4%,
    100% 88%, 96% 100%, 8% 100%, 0% 92%
  );
}

.card-shell:hover .assistant-card,
.assistant-card.is-active {
  transform: translateY(-0.625rem) scale(1.06);
  box-shadow:
    0 1.25rem 3rem rgba(15, 23, 42, 0.55),
    0 0 2.5rem rgba(56, 189, 248, 0.35),
    0 0 4rem rgba(139, 92, 246, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  filter: brightness(1.08);
}

.card-aura {
  position: absolute;
  inset: -20%;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.22) 0%, transparent 65%);
  opacity: 0;
  transition: opacity 0.38s ease;
  pointer-events: none;
  z-index: 0;
}

.card-shell:hover .card-aura,
.assistant-card.is-active .card-aura {
  opacity: 1;
}

.card-inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  height: 24rem;
  min-height: 24rem;
  border-radius: calc(1.75rem - 1px) calc(1.75rem - 1px) calc(2.25rem - 1px) calc(1.25rem - 1px);
  background:
    linear-gradient(165deg, rgba(15, 23, 42, 0.92) 0%, rgba(30, 27, 75, 0.88) 55%, rgba(15, 23, 42, 0.95) 100%);
  backdrop-filter: blur(1.25rem);
  overflow: hidden;
  clip-path: polygon(
    0% 4%, 4% 0%, 96% 0%, 100% 4%,
    100% 88%, 96% 100%, 8% 100%, 0% 92%
  );
}

.card-scanline {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(56, 189, 248, 0.04) 48%,
    transparent 100%
  );
  animation: scanMove 4s ease-in-out infinite;
  pointer-events: none;
}

.card-header {
  flex: 0 0 auto;
  padding: 1rem 1rem 0.5rem;
  text-align: center;
}

.title-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.875rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(56, 189, 248, 0.35);
  backdrop-filter: blur(8px);
  box-shadow: inset 0 0 12px rgba(56, 189, 248, 0.08);
}

.title-chip-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8;
  animation: dotPulse 2s ease-in-out infinite;
}

.card-title {
  margin: 0;
  font-size: clamp(0.875rem, 2vw, 1rem);
  font-weight: 700;
  letter-spacing: 0.05em;
  background: linear-gradient(180deg, #ffffff 0%, #bae6fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}

.card-body {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 0.5rem 1rem;
  min-height: 0;
}

.avatar-orbit {
  position: absolute;
  width: 72%;
  aspect-ratio: 1;
  border-radius: 50%;
  border: 1px dashed rgba(56, 189, 248, 0.25);
  animation: orbitSpin 12s linear infinite;
}

.avatar-ring {
  position: relative;
  padding: 3px;
  border-radius: 50%;
  background: linear-gradient(135deg, #38bdf8, #818cf8, #a78bfa, #38bdf8);
  background-size: 300% 300%;
  animation: ringGradient 4s ease infinite;
  box-shadow:
    0 0 1.5rem rgba(56, 189, 248, 0.4),
    0 0 2.5rem rgba(139, 92, 246, 0.2);
}

.avatar-frame {
  width: clamp(7rem, 28vw, 9.5rem);
  height: clamp(7rem, 28vw, 9.5rem);
  border-radius: 50%;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.9);
  border: 2px solid rgba(15, 23, 42, 0.8);
}

.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  display: block;
  transition: transform 0.38s cubic-bezier(0.34, 1.45, 0.64, 1);
}

.card-shell:hover .avatar {
  transform: scale(1.04);
}

.card-footer {
  flex: 0 0 auto;
  padding: 0 0.75rem 0.875rem;
}

.footer-mask {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.625rem 0.875rem;
  border-radius: 0.875rem;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(12px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.footer-label {
  font-size: 0.6875rem;
  color: #94a3b8;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.footer-action {
  font-size: 0.75rem;
  color: #7dd3fc;
  transition: color 0.3s ease;
}

.card-shell:hover .footer-action {
  color: #e0f2fe;
}

/* ── 详情浮层：叠在卡片上方，不被边框遮挡 ── */
.detail-panel {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: flex-end;
  padding: 0.625rem;
  pointer-events: none;
  border-radius: 1.75rem 1.75rem 2.25rem 1.25rem;
}

.detail-panel-inner {
  width: 100%;
  max-height: 72%;
  overflow-y: auto;
  padding: 0.875rem 1rem;
  border-radius: 0.875rem;
  pointer-events: auto;
  background: linear-gradient(
    180deg,
    rgba(15, 23, 42, 0.72) 0%,
    rgba(15, 23, 42, 0.94) 35%,
    rgba(30, 27, 75, 0.96) 100%
  );
  border: 1px solid rgba(56, 189, 248, 0.45);
  backdrop-filter: blur(1.25rem);
  box-shadow:
    0 -0.5rem 2rem rgba(15, 23, 42, 0.5),
    0 0 1.5rem rgba(56, 189, 248, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.detail-item + .detail-item {
  margin-top: 0.75rem;
}

.detail-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #38bdf8;
  margin-bottom: 0.375rem;
}

.detail-icon {
  display: inline-block;
  margin-right: 0.375rem;
  animation: iconPulse 1.5s ease-in-out infinite;
}

.detail-desc {
  margin: 0;
  font-size: 0.75rem;
  color: #94a3b8;
  line-height: 1.6;
}

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}

/* ── 浮动装饰 ── */
.floating-ai {
  position: fixed;
  right: clamp(1rem, 3vw, 2rem);
  bottom: clamp(1rem, 3vw, 2rem);
  z-index: 20;
}

.floating-avatar {
  width: 3.75rem;
  height: 3.75rem;
  border-radius: 50%;
  border: 3px solid #3b82f6;
  box-shadow: 0 0 30px rgba(59, 130, 246, 0.5);
  animation: avatarPulse 2s ease-in-out infinite;
  position: relative;
  z-index: 2;
}

.floating-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 5.625rem;
  height: 5.625rem;
  border: 2px dashed rgba(139, 92, 246, 0.5);
  border-radius: 50%;
  animation: floatingOrbit 8s linear infinite;
}

/* ── 动画 ── */
@keyframes textGradient {
  0% { background-position: 0% center; }
  100% { background-position: 200% center; }
}

@keyframes rotateHex {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes rotateHexReverse {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(-360deg); }
}

@keyframes dotFloat {
  0%, 100% { opacity: 0.4; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-0.625rem); }
}

@keyframes dotPulse {
  0%, 100% { box-shadow: 0 0 8px #38bdf8; }
  50% { box-shadow: 0 0 16px #38bdf8, 0 0 24px rgba(139, 92, 246, 0.5); }
}

@keyframes ringGradient {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

@keyframes orbitSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes scanMove {
  0%, 100% { transform: translateY(-100%); opacity: 0; }
  50% { transform: translateY(100%); opacity: 1; }
}

@keyframes iconPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

@keyframes avatarPulse {
  0%, 100% { box-shadow: 0 0 30px rgba(59, 130, 246, 0.5); }
  50% { box-shadow: 0 0 50px rgba(59, 130, 246, 0.7), 0 0 80px rgba(139, 92, 246, 0.4); }
}

@keyframes floatingOrbit {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

/* ── 响应式 ── */
@media (max-width: 992px) {
  .hero-decoration {
    display: none;
  }
}

@media (max-width: 768px) {
  .content {
    padding: 0.875rem 1rem 1.5rem;
  }

  .card-col {
    margin-bottom: 1.25rem;
  }

  .card-inner {
    height: clamp(20rem, 58vw, 24rem);
    min-height: clamp(20rem, 58vw, 24rem);
  }

  .card-shell {
    max-width: min(18rem, 88vw);
  }

  .assistant-card {
    border-radius: 1.5rem 1.5rem 1.75rem 1.125rem;
  }

  .card-shell:hover .assistant-card,
  .assistant-card.is-active {
    transform: translateY(-0.375rem) scale(1.03);
  }

  .detail-panel {
    position: absolute;
    inset: 0;
    width: 100%;
    margin-top: 0;
    padding: 0.5rem;
    border-radius: 1.5rem 1.5rem 1.75rem 1.125rem;
  }

  .detail-panel-inner {
    max-height: 68%;
  }

  .detail-fade-enter-from,
  .detail-fade-leave-to {
    transform: translateY(-0.375rem);
  }

  .floating-ai {
    display: none;
  }

  .card-title {
    white-space: normal;
    font-size: 0.875rem;
  }
}

@media (max-width: 480px) {
  .partners {
    gap: 0.5rem;
  }

  .partners :deep(.partner-tag.el-tag) {
    font-size: 0.75rem;
    padding: 0.375rem 0.75rem;
  }

  .footer-mask {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>

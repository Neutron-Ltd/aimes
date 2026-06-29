<template>
  <el-card class="assistant-page-header" shadow="never">
    <div class="assistant-page-header__body">
      <div class="assistant-page-header__wing assistant-page-header__wing--left" aria-hidden="true">
        <span class="assistant-page-header__dot"></span>
        <span class="assistant-page-header__line"></span>
        <span class="assistant-page-header__chevron"></span>
      </div>

      <div class="assistant-page-meta">
        <div class="assistant-page-title-badge">
          <span class="assistant-page-title-line assistant-page-title-line--top"></span>
          <h2>{{ title }}</h2>
          <span class="assistant-page-title-line assistant-page-title-line--bottom"></span>
        </div>
        <p>{{ subtitle }}</p>
      </div>

      <div class="assistant-page-header__wing assistant-page-header__wing--right" aria-hidden="true">
        <span class="assistant-page-header__chevron"></span>
        <span class="assistant-page-header__line"></span>
        <span class="assistant-page-header__dot"></span>
      </div>

      <el-tag effect="dark" round class="status-pill">{{ statusLabel }}</el-tag>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    required: true
  },
  statusLabel: {
    type: String,
    required: true
  }
})
</script>

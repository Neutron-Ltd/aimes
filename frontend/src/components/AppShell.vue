<template>
  <el-container class="app-container">
    <AppBackground />
    <AppHeader />
    <el-main class="app-main">
      <slot />
    </el-main>
  </el-container>
</template>

<script setup>
import AppBackground from './AppBackground.vue'
import AppHeader from './AppHeader.vue'
</script>

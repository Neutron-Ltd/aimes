<template>
  <div class="app-background-layer">
    <div class="background">
      <div class="bg-gradient"></div>
      <div class="bg-pattern"></div>
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
      <div class="particles">
        <div v-for="i in 50" :key="i" class="particle" :style="getParticleStyle()"></div>
      </div>
    </div>

    <div class="top-decoration">
      <div class="decoration-dot"></div>
      <div class="decoration-line"></div>
      <div class="decoration-dot"></div>
    </div>
  </div>
</template>

<script setup>
const getParticleStyle = () => ({
  left: Math.random() * 100 + '%',
  top: Math.random() * 100 + '%',
  animationDelay: Math.random() * 15 + 's',
  animationDuration: 10 + Math.random() * 20 + 's'
})
</script>

<style>
@import '../assets/styles/app.css';
</style>

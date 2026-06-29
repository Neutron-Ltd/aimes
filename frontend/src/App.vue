<template>
  <el-config-provider :locale="elementLocale">
    <AppShell>
      <RouterView />
    </AppShell>
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import AppShell from './components/AppShell.vue'
import { useLocale } from './composables/useLocale'

const { locale } = useLocale()

const elementLocale = computed(() => (locale.value === 'en' ? en : zhCn))
</script>

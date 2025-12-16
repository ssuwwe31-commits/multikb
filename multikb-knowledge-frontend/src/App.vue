<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/modules/app'
import { useUserStore } from '@/stores/modules/user'

const appStore = useAppStore()
const userStore = useUserStore()

onMounted(() => {
  appStore.initApp()
  userStore.initUser()
})
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}
</style>

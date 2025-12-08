<template>
  <div class="home">
    <Navbar />
    <Hero />
    <Features />
    <Comparison />
    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Hero from '../components/sections/Hero.vue'
import Features from '../components/sections/Features.vue'
import Comparison from '../components/sections/Comparison.vue'
import Footer from '../components/layout/Footer.vue'
</script>

<style scoped>
.home {
  min-height: 100vh;
}
</style>


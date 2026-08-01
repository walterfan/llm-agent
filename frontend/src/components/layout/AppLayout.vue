<script setup lang="ts">
import AppHeader from './AppHeader.vue'
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <AppHeader />
    <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>
  </div>
</template>

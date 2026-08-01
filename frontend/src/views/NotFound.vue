<script setup lang="ts">
import { RouterLink } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <div class="text-center py-12">
      <h1 class="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <p class="text-xl text-gray-600 mb-8">Page not found</p>
      <RouterLink
        to="/"
        class="inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
      >
        Go back home
      </RouterLink>
    </div>
  </AppLayout>
</template>

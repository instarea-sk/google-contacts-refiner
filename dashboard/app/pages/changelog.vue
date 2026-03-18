<script setup lang="ts">
useHead({
  title: 'Changelog — Contact Refiner',
  meta: [
    { name: 'description', content: 'Full history of all changes applied to your Google Contacts. Track every diacritics fix, formatting correction, and cleanup action.' },
  ],
})
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-xl font-bold text-neutral-100">
      Changelog
    </h1>
    <ChangelogTable />
  </div>
</template>

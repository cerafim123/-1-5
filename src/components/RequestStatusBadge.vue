<script setup>
defineProps({
  status: { type: String, required: true }
})
</script>

<template>
  <span class="status-badge" :class="`status-${status.replaceAll(' ', '-')}`">
    {{ status }}
  </span>
</template>
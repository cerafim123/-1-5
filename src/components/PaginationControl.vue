<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true }
})

defineEmits(['change'])
</script>

<template>
  <div class="pagination">
    <button :disabled="page <= 1" @click="$emit('change', page - 1)">
      Назад
    </button>
    <span>Страница {{ page }} из {{ totalPages }}</span>
    <button :disabled="page >= totalPages" @click="$emit('change', page + 1)">
      Далее
    </button>
  </div>
</template>

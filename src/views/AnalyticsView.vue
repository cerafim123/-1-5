<script setup>
import { computed, onMounted } from 'vue'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
onMounted(() => store.load())

const types = computed(() => {
  const result = {}
  for (const request of store.requests) {
    result[request.type] = (result[request.type] || 0) + 1
  }
  return result
})
</script>

<template>
  <section>
    <h1>Аналитика — предварительный экран</h1>
    <p>В ПР 4 показатели будут рассчитываться на сервере из базы данных.</p>

    <h2>Количество заявок по типам</h2>
    <ul>
      <li v-for="(count, type) in types" :key="type">
        {{ type }}: {{ count }}
      </li>
    </ul>
  </section>
</template>

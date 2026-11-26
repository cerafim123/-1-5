<script setup>
import { computed, onMounted } from 'vue'
import { useRequestsStore } from '../stores/requests'

const store = useRequestsStore()
onMounted(() => store.load())

const total = computed(() => store.requests.length)
const open = computed(() =>
  store.requests.filter(item => ['Новая', 'Назначена', 'В работе'].includes(item.status)).length
)
const overdueDemo = computed(() =>
  store.requests.filter(item => item.status === 'В работе').length
)
</script>

<template>
  <section>
    <h1>Главная</h1>
    <p>Интернет-приложение для учета обращений жильцов.</p>

    <div class="stats">
      <div class="stat-card"><span>Всего заявок</span><strong>{{ total }}</strong></div>
      <div class="stat-card"><span>Открытых заявок</span><strong>{{ open }}</strong></div>
      <div class="stat-card"><span>В работе</span><strong>{{ overdueDemo }}</strong></div>
    </div>

    <RouterLink class="button" to="/requests">Перейти к заявкам</RouterLink>
  </section>
</template>

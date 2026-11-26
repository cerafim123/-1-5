<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRequestsStore } from '../stores/requests'
import RequestStatusBadge from '../components/RequestStatusBadge.vue'

const route = useRoute()
const store = useRequestsStore()
onMounted(() => store.load())

const request = computed(() =>
  store.requests.find(item => item.id === Number(route.params.id))
)
</script>

<template>
  <section v-if="request">
    <RouterLink to="/requests">← К списку заявок</RouterLink>
    <h1>Заявка №{{ request.id }}</h1>
    <RequestStatusBadge :status="request.status"/>

    <div class="details-card">
      <p><strong>Адрес:</strong> {{ request.address }}, квартира {{ request.apartment }}</p>
      <p><strong>Тип:</strong> {{ request.type }}</p>
      <p><strong>Приоритет:</strong> {{ request.priority }}</p>
      <p><strong>Описание:</strong> {{ request.description }}</p>
      <p><strong>Дата создания:</strong> {{ request.createdAt }}</p>
      <p><strong>Мастер:</strong> {{ request.master || 'Не назначен' }}</p>
    </div>
  </section>

  <section v-else>
    <h1>Заявка не найдена</h1>
    <RouterLink to="/requests">Вернуться к списку</RouterLink>
  </section>
</template>

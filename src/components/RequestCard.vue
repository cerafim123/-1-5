<script setup>
import RequestStatusBadge from './RequestStatusBadge.vue'

defineProps({
  request: { type: Object, required: true }
})
</script>

<template>
  <article class="request-card">
    <div class="request-card__top">
      <strong>Заявка №{{ request.id }}</strong>
      <RequestStatusBadge :status="request.status" />
    </div>

    <p><strong>Адрес:</strong> {{ request.address }}, кв. {{ request.apartment }}</p>
    <p><strong>Тип:</strong> {{ request.type }} · <strong>Приоритет:</strong> {{ request.priority }}</p>
    <p>{{ request.description }}</p>
    <small>Создана: {{ request.createdAt }}</small>
    <RouterLink class="button button-link" :to="`/requests/${request.id}`">
      Открыть
    </RouterLink>
  </article>
</template>

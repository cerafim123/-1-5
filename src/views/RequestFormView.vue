<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRequestsStore } from '../stores/requests'

const router = useRouter()
const store = useRequestsStore()
const error = ref('')

const form = reactive({
  address: '',
  apartment: '',
  type: '',
  description: '',
  priority: 'Обычный'
})

function submit() {
  error.value = ''

  if (!form.address.trim()) {
    error.value = 'Укажите адрес дома.'
    return
  }

  if (!form.apartment.trim()) {
    error.value = 'Укажите номер квартиры.'
    return
  }

  if (!form.type) {
    error.value = 'Выберите тип заявки.'
    return
  }

  if (form.description.trim().length < 10) {
    error.value = 'Описание должно содержать не менее 10 символов.'
    return
  }

  const request = store.create({
    ...form,
    address: form.address.trim(),
    apartment: form.apartment.trim(),
    description: form.description.trim()
  })

  router.push(`/requests/${request.id}`)
}
</script>

<template>
  <section class="form-page">
    <h1>Новая заявка</h1>

    <form class="request-form" @submit.prevent="submit">
      <label class="field">
        <span>Адрес дома *</span>
        <input v-model="form.address" placeholder="Например, ул. Лесная, 12">
      </label>

      <label class="field">
        <span>Квартира *</span>
        <input v-model="form.apartment" placeholder="Номер квартиры">
      </label>

      <label class="field">
        <span>Тип заявки *</span>
        <select v-model="form.type">
          <option value="">Выберите тип</option>
          <option>Сантехника</option>
          <option>Электрика</option>
          <option>Отопление</option>
          <option>Уборка</option>
          <option>Ремонт подъезда</option>
        </select>
      </label>

      <label class="field">
        <span>Приоритет</span>
        <select v-model="form.priority">
          <option>Низкий</option>
          <option>Обычный</option>
          <option>Высокий</option>
        </select>
      </label>

      <label class="field">
        <span>Описание проблемы *</span>
        <textarea v-model="form.description" rows="5"/>
      </label>

      <p v-if="error" class="error-message">{{ error }}</p>
      <button class="button" type="submit">Создать заявку</button>
    </form>
  </section>
</template>

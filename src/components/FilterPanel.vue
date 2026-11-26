<script setup>
defineProps({
  status: { type: String, default: '' },
  type: { type: String, default: '' }
})

defineEmits(['update:status', 'update:type'])
</script>

<template>
  <div class="filters">
    <label class="field">
      <span>Статус</span>
      <select :value="status" @change="$emit('update:status', $event.target.value)">
        <option value="">Все статусы</option>
        <option>Новая</option>
        <option>Назначена</option>
        <option>В работе</option>
        <option>Выполнена</option>
        <option>Отменена</option>
      </select>
    </label>

    <label class="field">
      <span>Тип заявки</span>
      <select :value="type" @change="$emit('update:type', $event.target.value)">
        <option value="">Все типы</option>
        <option>Сантехника</option>
        <option>Электрика</option>
        <option>Отопление</option>
        <option>Уборка</option>
        <option>Ремонт подъезда</option>
      </select>
    </label>
  </div>
</template>

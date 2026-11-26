<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Поиск' }
})

defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span>Поиск</span>
    <input
      :value="modelValue"
      :placeholder="placeholder"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  </label>
</template>

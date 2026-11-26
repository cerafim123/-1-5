<script setup>
const houses = [
  { address: 'ул. Лесная, 12', apartments: 36 },
  { address: 'ул. Лесная, 14', apartments: 48 },
  { address: 'ул. Садовая, 3', apartments: 32 },
  { address: 'ул. Садовая, 8', apartments: 40 },
  { address: 'пр. Мира, 25', apartments: 56 }
]
</script>

<template>
  <section>
    <h1>Дома</h1>
    <ul class="house-list">
      <li v-for="house in houses" :key="house.address">
        <strong>{{ house.address }}</strong>
        <span>{{ house.apartments }} квартир</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRequestsStore } from '../stores/requests'
import SearchField from '../components/SearchField.vue'
import FilterPanel from '../components/FilterPanel.vue'
import RequestCard from '../components/RequestCard.vue'
import PaginationControl from '../components/PaginationControl.vue'

const store = useRequestsStore()
onMounted(() => store.load())

const search = ref('')
const status = ref('')
const type = ref('')
const sortOrder = ref('newest')
const page = ref(1)
const pageSize = 5

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()

  const result = store.requests.filter(request => {
    const textMatch = !query ||
      request.address.toLowerCase().includes(query) ||
      request.description.toLowerCase().includes(query)

    return textMatch &&
      (!status.value || request.status === status.value) &&
      (!type.value || request.type === type.value)
  })

  return [...result].sort((a, b) =>
    sortOrder.value === 'newest'
      ? b.createdAt.localeCompare(a.createdAt)
      : a.createdAt.localeCompare(b.createdAt)
  )
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))

const visibleRequests = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <h1>Заявки</h1>
        <p>Найдено: {{ filtered.length }}</p>
      </div>
      <RouterLink class="button" to="/requests/new">Создать заявку</RouterLink>
    </div>

    <div class="toolbar">
      <SearchField v-model="search" placeholder="Адрес или описание"/>
      <FilterPanel v-model:status="status" v-model:type="type"/>
      <label class="field">
        <span>Сортировка</span>
        <select v-model="sortOrder">
          <option value="newest">Сначала новые</option>
          <option value="oldest">Сначала старые</option>
        </select>
      </label>
    </div>

    <div v-if="visibleRequests.length" class="request-list">
      <RequestCard
        v-for="request in visibleRequests"
        :key="request.id"
        :request="request"
      />
    </div>
    <p v-else class="empty-state">Заявки не найдены.</p>

    <PaginationControl
      :page="page"
      :total-pages="totalPages"
      @change="page = $event"
    />
  </section>
</template>

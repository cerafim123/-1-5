<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { analyticsApi } from '../api/analytics'

const filters = reactive({
  date_from: '',
  date_to: '',
  house_id: ''
})

const now = new Date()
const reportMonth = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
)

const dashboard = ref(null)
const houses = ref([])
const loading = ref(false)
const downloading = ref(false)
const errorMessage = ref('')

const monthlyCanvas = ref(null)
const houseCanvas = ref(null)
const typeCanvas = ref(null)

let monthlyChart = null
let houseChart = null
let typeChart = null

const indicators = computed(() => dashboard.value?.indicators ?? {
  total_requests: 0,
  overdue_requests: 0,
  completed_requests: 0
})

function destroyCharts() {
  monthlyChart?.destroy()
  houseChart?.destroy()
  typeChart?.destroy()

  monthlyChart = null
  houseChart = null
  typeChart = null
}

function renderCharts(data) {
  destroyCharts()

  const ChartConstructor = window.Chart

  if (!ChartConstructor) {
    errorMessage.value = 'Chart.js не загружен. Проверьте подключение CDN в index.html.'
    return
  }

  const monthly = data.monthly_requests ?? []
  const byHouse = data.requests_by_house ?? []
  const byType = data.requests_by_type ?? []

  if (monthlyCanvas.value) {
    monthlyChart = new ChartConstructor(monthlyCanvas.value, {
      type: 'line',
      data: {
        labels: monthly.map(item => item.month),
        datasets: [{
          label: 'Количество заявок',
          data: monthly.map(item => item.count),
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.15)',
          fill: true,
          tension: 0.25
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
            title: { display: true, text: 'Количество заявок' }
          },
          x: {
            title: { display: true, text: 'Месяц' }
          }
        }
      }
    })
  }

  if (houseCanvas.value) {
    houseChart = new ChartConstructor(houseCanvas.value, {
      type: 'bar',
      data: {
        labels: byHouse.map(item => item.house),
        datasets: [{
          label: 'Количество заявок',
          data: byHouse.map(item => item.count),
          backgroundColor: '#60a5fa',
          borderColor: '#2563eb',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: {
            beginAtZero: true,
            ticks: { precision: 0 },
            title: { display: true, text: 'Количество заявок' }
          }
        }
      }
    })
  }

  if (typeCanvas.value) {
    const sortedTypes = [...byType].sort((a, b) => b.count - a.count)
    const visibleTypes = sortedTypes.slice(0, 5)
    const otherCount = sortedTypes
      .slice(5)
      .reduce((sum, item) => sum + item.count, 0)

    if (otherCount > 0) {
      visibleTypes.push({ type: 'Другие', count: otherCount })
    }

    typeChart = new ChartConstructor(typeCanvas.value, {
      type: 'doughnut',
      data: {
        labels: visibleTypes.map(item => item.type),
        datasets: [{
          data: visibleTypes.map(item => item.count),
          backgroundColor: [
            '#2563eb',
            '#10b981',
            '#f59e0b',
            '#ef4444',
            '#8b5cf6',
            '#94a3b8'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    })
  }
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''

  try {
    dashboard.value = await analyticsApi.getDashboard(filters)
    renderCharts(dashboard.value)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

function saveFile(blob, filename) {
  const url =URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()

  URL.revokeObjectURL(url)
}

async function downloadHouseReport() {
  if (!filters.house_id) {
    errorMessage.value = 'Для XLSX-отчёта выберите дом.'
    return
  }

  if (!reportMonth.value) {
    errorMessage.value = 'Выберите месяц для XLSX-отчёта.'
    return
  }

  downloading.value = true
  errorMessage.value = ''

  try {
    const [year, month] = reportMonth.value.split('-').map(Number)
    const response = await analyticsApi.downloadHouseMonth({
      house_id: filters.house_id,
      year,
      month
    })

    saveFile(
      await response.blob(),
      `house_${filters.house_id}_${year}_${String(month).padStart(2, '0')}.xlsx`
    )
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    downloading.value = false
  }
}

async function downloadOverdueReport() {
  downloading.value = true
  errorMessage.value = ''

  try {
    const response = await analyticsApi.downloadOverdue(filters)
    saveFile(await response.blob(), 'overdue_requests.pdf')
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  try {
    houses.value = await analyticsApi.getHouses()
  } catch (error) {
    errorMessage.value = error.message
  }

  await loadDashboard()
})

onBeforeUnmount(destroyCharts)
</script>

<template>
  <main class="analytics-page">
    <header>
      <h1>Аналитика заявок</h1>
      <p>Сводные показатели по заявкам жильцов</p>
    </header>

    <form class="analytics-filters" @submit.prevent="loadDashboard">
      <label>
        <span>Дата с</span>
        <input v-model="filters.date_from" type="date">
      </label>

      <label>
        <span>Дата по</span>
        <input v-model="filters.date_to" type="date">
      </label>

      <label>
        <span>Дом</span>
        <select v-model="filters.house_id">
          <option value="">Все дома</option>
          <option
            v-for="house in houses"
            :key="house.id"
            :value="house.id"
          >
            {{ house.address }}
          </option>
        </select>
      </label>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Загрузка…' : 'Применить фильтры' }}
      </button>
    </form>

    <p v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </p>

    <section class="indicator-grid">
      <article class="indicator-card">
        <h2>Всего заявок</h2>
        <strong>{{ indicators.total_requests }}</strong>
      </article>

      <article class="indicator-card">
        <h2>Просрочено</h2>
        <strong>{{ indicators.overdue_requests }}</strong>
      </article>

      <article class="indicator-card">
        <h2>Выполнено</h2>
        <strong>{{ indicators.completed_requests }}</strong>
      </article>
    </section>

    <section class="chart-grid">
      <article class="chart-card">
        <h2>Динамика заявок по месяцам</h2>
        <div class="chart-area">
          <canvas ref="monthlyCanvas"></canvas>
        </div>
      </article>

      <article class="chart-card">
        <h2>Заявки по домам</h2>
        <div class="chart-area">
          <canvas ref="houseCanvas"></canvas>
        </div>
      </article>

      <article class="chart-card chart-card-wide">
        <h2>Заявки по типам</h2>
        <div class="chart-area">
          <canvas ref="typeCanvas"></canvas>
        </div>
      </article>
    </section>

    <section class="report-section">
      <h2>Документы</h2>

      <div class="report-controls">
        <label>
          <span>Месяц для сводки по дому</span>
          <input v-model="reportMonth" type="month">
        </label>

        <button
          type="button"
          :disabled="downloading"
          @click="downloadHouseReport"
        >
          Скачать сводку по дому (XLSX)
        </button>

        <button
          type="button"
          :disabled="downloading"
          @click="downloadOverdueReport"
        >
          Скачать просроченные заявки (PDF)
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.analytics-page {
  display: grid;
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.analytics-page h1,
.analytics-page h2 {
  margin-top: 0;
}

.analytics-filters,
.report-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 16px;
}

.analytics-filters label,
.report-controls label {
  display: grid;
  gap: 6px;
}

.analytics-filters input,
.analytics-filters select,
.report-controls input {
  min-height: 40px;
  padding: 8px 10px;
}

.analytics-filters button,
.report-controls button {
  min-height: 40px;
  padding: 8px 14px;
  cursor: pointer;
}

.indicator-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.indicator-card,
.chart-card,
.report-section {
  padding: 18px;
  border: 1px solid #dbe2ea;
  border-radius: 12px;
  background: #fff;
}

.indicator-card h2 {
  margin-bottom: 12px;
  font-size: 16px;
}

.indicator-card strong {
  font-size: 30px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.chart-card-wide {
  grid-column: 1 / -1;
}

.chart-area {
  position: relative;
  height: 300px;
}

.error-message {
  color: #b91c1c;
}

@media(max-width: 700px) {
  .analytics-page {
    padding: 16px;
  }

  .indicator-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-card-wide {
    grid-column: auto;
  }

  .chart-area {
    height: 260px;
  }
}
</style>
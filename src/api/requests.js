const STORAGE_KEY = 'uk-requests'

const initialRequests = [
  { id: 1, address: 'ул. Лесная, 12', apartment: '15', type: 'Сантехника', description: 'Протекает кран на кухне', priority: 'Обычный', status: 'Новая', createdAt: '2026-09-02', master: '' },
  { id: 2, address: 'ул. Лесная, 12', apartment: '28', type: 'Электрика', description: 'Не работает освещение в коридоре', priority: 'Высокий', status: 'Назначена', createdAt: '2026-09-04', master: 'Иванов И.И.' },
  { id: 3, address: 'ул. Лесная, 14', apartment: '7', type: 'Отопление', description: 'Холодная батарея в комнате', priority: 'Высокий', status: 'В работе', createdAt: '2026-09-05', master: 'Петров П.П.' },
  { id: 4, address: 'ул. Садовая, 3', apartment: '41', type: 'Уборка', description: 'Необходимо убрать лестничную площадку', priority: 'Низкий', status: 'Выполнена', createdAt: '2026-09-06', master: 'Сидоров С.С.' },
  { id: 5, address: 'ул. Садовая, 3', apartment: '12', type: 'Ремонт подъезда', description: 'Повреждена штукатурка у входа', priority: 'Обычный', status: 'Назначена', createdAt: '2026-09-08', master: 'Иванов И.И.' },
  { id: 6, address: 'пр. Мира, 25', apartment: '8', type: 'Сантехника', description: 'Засорилась раковина', priority: 'Обычный', status: 'В работе', createdAt: '2026-09-10', master: 'Петров П.П.' },
  { id: 7, address: 'пр. Мира, 25', apartment: '33', type: 'Электрика', description: 'Искрит выключатель', priority: 'Высокий', status: 'Новая', createdAt: '2026-09-11', master: '' },
  { id: 8, address: 'ул. Лесная, 14', apartment: '19', type: 'Уборка', description: 'Загрязнена площадка возле лифта', priority: 'Низкий', status: 'Выполнена', createdAt: '2026-09-12', master: 'Сидоров С.С.' },
  { id: 9, address: 'ул. Садовая, 8', apartment: '5', type: 'Отопление', description: 'Слабый нагрев радиатора', priority: 'Обычный', status: 'Назначена', createdAt: '2026-09-14', master: 'Петров П.П.' },
  { id: 10, address: 'ул. Садовая, 8', apartment: '22', type: 'Сантехника', description: 'Подтекает труба под раковиной', priority: 'Высокий', status: 'В работе', createdAt: '2026-09-15', master: 'Иванов И.И.' },
  { id: 11, address: 'пр. Мира, 25', apartment: '17', type: 'Ремонт подъезда', description: 'Сломана дверная ручка в подъезде', priority: 'Низкий', status: 'Отменена', createdAt: '2026-09-17', master: '' },
  { id: 12, address: 'ул. Лесная, 12', apartment: '6', type: 'Электрика', description: 'Не работает розетка в комнате', priority: 'Обычный', status: 'Выполнена', createdAt: '2026-09-19', master: 'Иванов И.И.' },
  { id: 13, address: 'ул. Садовая, 3', apartment: '30', type: 'Отопление', description: 'Нужно проверить батарею', priority: 'Обычный', status: 'Новая', createdAt: '2026-09-20', master: '' },
  { id: 14, address: 'ул. Лесная, 14', apartment: '11', type: 'Сантехника', description: 'Неисправен сливной бачок', priority: 'Высокий', status: 'В работе', createdAt: '2026-09-22', master: 'Петров П.П.' },
  { id: 15, address: 'ул. Садовая, 8', apartment: '9', type: 'Уборка', description: 'Убрать мусор у входа в дом', priority: 'Низкий', status: 'Выполнена', createdAt: '2026-09-24', master: 'Сидоров С.С.' }
]

function readRequests() {
  const saved = localStorage.getItem(STORAGE_KEY)

  if (saved) {
    try {
      return JSON.parse(saved)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(initialRequests))
  return [...initialRequests]
}

function saveRequests(requests) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(requests))
}

export const requestsApi = {
  getAll() {
    return readRequests()
  },

  getById(id) {
    return readRequests().find(request => request.id === Number(id)) ?? null
  },

  create(data) {
    const requests = readRequests()
    const newRequest = {
      ...data,
      id: Math.max(0, ...requests.map(request => request.id)) + 1,
      status: 'Новая',
      master: '',
      createdAt: new Date().toISOString().slice(0, 10)
    }

    requests.unshift(newRequest)
    saveRequests(requests)
    return newRequest
  },

  update(id, changes) {
    const requests = readRequests()
    const index = requests.findIndex(request => request.id === Number(id))

    if (index === -1) return null

    requests[index] = { ...requests[index], ...changes }
    saveRequests(requests)
    return requests[index]
  }
}
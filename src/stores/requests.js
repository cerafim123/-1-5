import { defineStore } from 'pinia'
import { requestsApi } from '../api/requests'

export const useRequestsStore = defineStore('requests', {
  state: () => ({
    requests: [],
    loaded: false
  }),

  actions: {
    load() {
      this.requests = requestsApi.getAll()
      this.loaded = true
    },

    create(data) {
      const request = requestsApi.create(data)
      this.requests = requestsApi.getAll()
      return request
    },

    update(id, changes) {
      const updated = requestsApi.update(id, changes)
      this.requests = requestsApi.getAll()
      return updated
    }
  }
})
import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import RequestsView from '../views/RequestsView.vue'
import RequestFormView from '../views/RequestFormView.vue'
import RequestDetailsView from '../views/RequestDetailsView.vue'
import HousesView from '../views/HousesView.vue'
import AnalyticsView from '../views/AnalyticsView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/requests', component: RequestsView },
    { path: '/requests/new', component: RequestFormView },
    { path: '/requests/:id', component: RequestDetailsView },
    { path: '/houses', component: HousesView },
    { path: '/analytics', component: AnalyticsView },
    { path: '/:pathMatch(.*)*', component: NotFoundView }
  ]
})

export default router

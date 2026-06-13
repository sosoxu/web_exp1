import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/experiments'
    },
    {
      path: '/experiments',
      name: 'ExperimentList',
      component: () => import('../views/ExperimentList.vue')
    },
    {
      path: '/experiment/new',
      name: 'NewExperiment',
      component: () => import('../views/ExperimentWorkspace.vue')
    },
    {
      path: '/experiment/:id',
      name: 'ExperimentDetail',
      component: () => import('../views/ExperimentWorkspace.vue'),
      props: true
    }
  ]
})

export default router

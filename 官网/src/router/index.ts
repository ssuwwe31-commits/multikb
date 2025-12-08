import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: Home
    },
    {
      path: '/features',
      name: 'Features',
      component: () => import('../views/Features.vue')
    },
    {
      path: '/docs',
      name: 'Docs',
      component: () => import('../views/Docs.vue')
    },
    {
      path: '/contact',
      name: 'Contact',
      component: () => import('../views/Contact.vue')
    },
    {
      path: '/pricing',
      name: 'Pricing',
      component: () => import('../views/Pricing.vue')
    },
    {
      path: '/cases',
      name: 'Cases',
      component: () => import('../views/Cases.vue')
    },
    {
      path: '/docs/:id',
      name: 'DocDetail',
      component: () => import('../views/DocDetail.vue')
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('../views/About.vue')
    },
    {
      path: '/privacy',
      name: 'Privacy',
      component: () => import('../views/Privacy.vue')
    },
    {
      path: '/terms',
      name: 'Terms',
      component: () => import('../views/Terms.vue')
    },
    {
      path: '/changelog',
      name: 'Changelog',
      component: () => import('../views/Changelog.vue')
    }
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

export default router


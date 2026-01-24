import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import HomeView from '../views/HomeView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    { path: '/admin', name: 'admin', component: AdminUsersView, meta: { requiresAuth: true, /*requiresAdmin: true*/ } },
  ]
})

// ✅ Router guard an toàn
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = JSON.parse(localStorage.getItem('user'))
  //login
if (to.meta.requiresAuth && !token) {
  return next('/login')
} 

if (to.meta.requiresAdmin && (!user || user.role !== 'admin')){
  alert('Bạn ko có quyền truy cập trang này')
  return next('/')
}

next()
})

export default router

<template>
  <nav class="navbar">
    <div class="navbar-left">
      <span class="brand">Chatbot DUT </span>
    </div>

    <div class="navbar-right" v-if="auth.user">
      <span class="username">{{ auth.user.name }}</span>
      <button @click="logout" class="logout-btn">Đăng xuất</button>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '../store/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: linear-gradient(135deg, #1a237e, #3949ab);
  color: white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
}

/* Logo / tiêu đề */
.brand {
  font-size: 20px;
  font-weight: bold;
}

/* Khu vực bên phải */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  font-weight: 500;
}

/* Nút đăng xuất */
.logout-btn {
  background-color: #e53935;
  border: none;
  color: white;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.logout-btn:hover {
  background-color: #c62828;
}
</style>

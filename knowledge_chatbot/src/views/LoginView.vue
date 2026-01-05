<template>
  <div class="login-page">
    <div class="login-card">
      <h2>Đăng nhập</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Tên đăng nhập</label>
          <input v-model="username" placeholder="Nhập username..." />
        </div>

        <div class="form-group">
          <label>Mật khẩu</label>
          <input v-model="password" type="password" placeholder="Nhập mật khẩu..." />
        </div>

        <button class="login-btn">Đăng nhập</button>
        <p class="error" v-if="error">{{ error }}</p>
      </form>

      <p class="register-link">
        Chưa có tài khoản?
        <router-link to="/register">Đăng ký ngay</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')

async function handleLogin() {
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/') // hoặc /chatbot nếu bạn cấu hình route riêng
  } catch (err) {
    error.value = err.message || 'Đăng nhập thất bại'
  }
}
</script>


<style scoped>
/* ✅ Toàn màn hình với gradient */
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(120deg, #667eea, #764ba2);
  background-size: cover;
  background-position: center;
  overflow: hidden;
}

/* Khung form giữa màn hình */
.login-card {
  background: rgba(255, 255, 255, 0.95);
  padding: 40px 50px;
  border-radius: 15px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 400px;
  text-align: center;
  animation: fadeIn 0.6s ease-in-out;
}

h2 {
  margin-bottom: 20px;
  color: #333;
  font-weight: 600;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

label {
  display: block;
  font-size: 14px;
  margin-bottom: 6px;
  color: #555;
}

input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #ccc;
  font-size: 15px;
  outline: none;
  transition: 0.2s;
}

input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.login-btn {
  width: 100%;
  background: #667eea;
  border: none;
  color: white;
  padding: 12px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.3s;
}

.login-btn:hover {
  background: #5563de;
  transform: translateY(-1px);
}

.error {
  color: #e74c3c;
  margin-top: 10px;
  font-size: 14px;
}

.register-link {
  margin-top: 20px;
  font-size: 14px;
  color: #555;
}

.register-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
}

.register-link a:hover {
  text-decoration: underline;
}

/* Hiệu ứng xuất hiện */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

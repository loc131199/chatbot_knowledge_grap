<template>
  <div class="register-page">
    <div class="register-card">
      <h2>Đăng ký tài khoản</h2>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>Tên đăng nhập</label>
          <input v-model="username" placeholder="Nhập username..." />
        </div>

        <div class="form-group">
          <label>Mật khẩu</label>
          <input v-model="password" type="password" placeholder="Nhập mật khẩu..." />
        </div>

        <div class="form-group">
          <label>Xác nhận mật khẩu</label>
          <input v-model="confirmPassword" type="password" placeholder="Nhập lại mật khẩu..." />
        </div>

        <button class="register-btn">Đăng ký</button>
        <p class="error" v-if="error">{{ error }}</p>
        <p class="success" v-if="success">{{ success }}</p>
      </form>

      <p class="login-link">
        Đã có tài khoản?
        <router-link to="/login">Đăng nhập ngay</router-link>
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
const confirmPassword = ref('')
const error = ref('')
const success = ref('')

async function handleRegister() {
  error.value = ''
  success.value = ''

  if (!username.value || !password.value || !confirmPassword.value) {
    error.value = 'Vui lòng điền đầy đủ thông tin.'
    return
  }

  if (password.value !== confirmPassword.value) {
    error.value = 'Mật khẩu xác nhận không khớp.'
    return
  }

  try {
    await auth.register(username.value, password.value)
    success.value = 'Đăng ký thành công! Chuyển sang đăng nhập...'
    setTimeout(() => router.push('/login'), 1500)
  } catch (err) {
    error.value = err.message || 'Đăng ký thất bại'
  }
}
</script>


<style scoped>
/* Toàn màn hình gradient */
.register-page {
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

/* Form giữa màn hình */
.register-card {
  background: rgba(255, 255, 255, 0.95);
  padding: 40px 50px;
  border-radius: 15px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 420px;
  text-align: center;
  animation: fadeIn 0.6s ease-in-out;
}

/* Tiêu đề */
h2 {
  margin-bottom: 20px;
  color: #333;
  font-weight: 600;
}

/* Form */
.form-group {
  margin-bottom: 18px;
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

/* Nút đăng ký */
.register-btn {
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

.register-btn:hover {
  background: #5563de;
  transform: translateY(-1px);
}

/* Thông báo */
.error {
  color: #e74c3c;
  margin-top: 10px;
  font-size: 14px;
}

.success {
  color: #2ecc71;
  margin-top: 10px;
  font-size: 14px;
}

/* Link đăng nhập */
.login-link {
  margin-top: 20px;
  font-size: 14px;
  color: #555;
}

.login-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
}

.login-link a:hover {
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

<template>
  <nav class="navbar">
    <div class="navbar-left">
      <span class="brand">Chatbot DUT </span>
    </div>

    <div class="navbar-right" v-if="auth.user">
      <span class="username">{{ auth.user.username }}</span>
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
  padding: 16px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15), 0 2px 6px rgba(0, 0, 0, 0.1);
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.navbar:hover {
  box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2), 0 3px 8px rgba(0, 0, 0, 0.15);
}

/* Logo / tiêu đề */
.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.brand:hover {
  transform: scale(1.05);
}

/* Khu vực bên phải */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-right: inherit;
}

.username {
  font-weight: 600;
  font-size: 15px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.username::before {
  content: "👤";
  font-size: 16px;
}

.username:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Nút đăng xuất */
.logout-btn {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
  border: none;
  color: white;
  padding: 10px 20px;
  border-radius: 25px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.3px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(238, 90, 111, 0.4);
  position: relative;
  overflow: hidden;
}

.logout-btn::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.logout-btn:hover::before {
  width: 300px;
  height: 300px;
}

.logout-btn:hover {
  background: linear-gradient(135deg, #ff5252 0%, #e53935 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(238, 90, 111, 0.5);
}

.logout-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 10px rgba(238, 90, 111, 0.4);
}

/* Responsive design */
@media (max-width: 768px) {
  .navbar {
    padding: 12px 20px;
  }

  .brand {
    font-size: 20px;
  }

  .username {
    font-size: 13px;
    padding: 6px 12px;
  }

  .username::before {
    display: none;
  }

  .logout-btn {
    padding: 8px 16px;
    font-size: 13px;
  }

  .navbar-right {
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .navbar {
    padding: 10px 16px;
  }

  .brand {
    font-size: 18px;
  }

  .username {
    display: none;
  }
}
</style>

<template>
  <div id="app">
    <Navbar v-if="auth.access_token" />

    <main class="page-container">
      <router-view />
    </main>
  </div>
</template>


<script setup>
import Navbar from './components/Navbar.vue'
import { useAuthStore } from './store/auth'

const auth = useAuthStore()
</script>

<style>
  .page-container {
  width: 100%;
  padding-top: 64px; /* chiều cao navbar */
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  margin: 0;
  background-color: #f8f9fa;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>

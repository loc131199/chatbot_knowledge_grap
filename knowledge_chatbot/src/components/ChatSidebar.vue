<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <span> Các đoạn chat của bạn</span>
      <button @click="$emit('new-chat')">+</button>
    </div>

    <div class="conversation-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === activeId }"
        @click="$emit('select', conv.id)"
      >
        <div class="title">
          {{ conv.title || 'Đoạn chat mới' }}
        </div>
        <div class="time">
          {{ formatTime(conv.updated_at) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    conversations: Array,
    activeId: Number,
  },
  methods: {
    formatTime(time) {
      return new Date(time).toLocaleDateString('vi-VN');
    },
  },
};
</script>

<style scoped>
.sidebar {
  width: 260px;
  height: calc(100vh - 64px);
  background: #f4f6fb;
  border-right: 1px solid #ddd;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  font-weight: bold;
  background: #e8eaf6;
}

.sidebar-header button {
  background: #1a237e;
  color: white;
  border: none;
  border-radius: 6px;
  width: 28px;
  height: 28px;
  cursor: pointer;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
}

.conversation-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #e0e0e0;
}

.conversation-item:hover {
  background: #e3f2fd;
}

.conversation-item.active {
  background: #c5cae9;
}

.title {
  font-size: 14px;
  font-weight: 500;
}

.time {
  font-size: 12px;
  color: #666;
}
</style>

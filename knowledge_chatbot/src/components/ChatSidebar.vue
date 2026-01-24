<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h3>Lịch sử Chat</h3>
      <button class="new-chat-btn" @click="$emit('new-chat')" title="Cuộc trò chuyện mới">
        <span class="icon">✎</span>
      </button>
    </div>

    <div class="conversation-list">
      <div v-if="conversations.length === 0" class="empty-conversations">
        <div class="empty-icon">📋</div>
        <p>Chưa có cuộc trò chuyện</p>
      </div>
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === activeId }"
        @click="$emit('select', conv.id)"
      >
        <div class="item-content">
          <div class="title">
            {{ conv.title || 'Đoạn chat mới' }}
          </div>
          <div class="time">
            {{ formatTime(conv.created_at) }}
          </div>
        </div>
        <button
          class="delete-btn"
          @click.stop="deleteConversation(conv.id)"
          title="Xoá conversation"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { deleteConversation as deleteConversationAPI } from '../services/api';

export default {
  props: {
    conversations: Array,
    activeId: Number,
  },
  methods: {
    formatTime(time) {
      const date = new Date(time);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);

      if (date.toDateString() === today.toDateString()) {
        return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Hôm qua';
      } else {
        return date.toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' });
      }
    },
    async deleteConversation(conversationId) {
      if (confirm('Bạn có chắc chắn muốn xoá conversation này?')) {
        try {
          await deleteConversationAPI(conversationId);
          this.$emit('delete', conversationId);
        } catch (error) {
          console.error('Lỗi khi xoá conversation:', error);
          alert('Không thể xoá conversation');
        }
      }
    }
  },
};
</script>

<style scoped>
.sidebar1 {
  width: 280px;
  height: calc(100vh - 64px);
  background: linear-gradient(180deg, #f5f7fa 0%, #eef2f7 100%);
  border-right: 1px solid #e0e4eb;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.sidebar {
  width: 280px;
  /* flex: 1; */
  display: flex;
  flex-direction: column;
  background: white;
  margin: 12px 12px 12px 0;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.new-chat-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  width: 36px;
  height: 36px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 16px;
}

.new-chat-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: scale(1.05);
}

.new-chat-btn:active {
  transform: scale(0.95);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-list::-webkit-scrollbar {
  width: 6px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: #d0d4db;
  border-radius: 3px;
}

.conversation-list::-webkit-scrollbar-thumb:hover {
  background: #b0b4bb;
}

.empty-conversations {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #999;
  font-size: 14px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.6;
}

.conversation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 6px;
  cursor: pointer;
  border-radius: 10px;
  background: white;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  gap: 8px;
}

.conversation-item:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
  border-color: rgba(102, 126, 234, 0.2);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.conversation-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.conversation-item.active .title,
.conversation-item.active .time {
  color: white;
}

.conversation-item.active .delete-btn {
  color: rgba(255, 255, 255, 0.8);
}

.conversation-item.active .delete-btn:hover {
  color: white;
}

.item-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.title {
  font-size: 14px;
  font-weight: 500;
  color: #2c3e50;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.time {
  font-size: 12px;
  color: #999;
  letter-spacing: 0.2px;
}

.delete-btn {
  background: none;
  border: none;
  color: #ccc;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  transition: all 0.2s ease;
  opacity: 0;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
  color: #ff6b6b;
}

.delete-btn:hover {
  background: rgba(255, 107, 107, 0.1);
  color: #d32f2f;
  transform: scale(1.1);
}

.delete-btn:active {
  transform: scale(0.95);
}

@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }

  .sidebar-header h3 {
    font-size: 14px;
  }

  .title {
    font-size: 13px;
  }

  .time {
    font-size: 11px;
  }
}
</style>

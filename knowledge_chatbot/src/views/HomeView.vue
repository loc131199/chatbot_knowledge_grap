<template>
  <div class="home-wrapper">
    <div class="chat-layout">
      <ChatSidebar
        :conversations="conversations"
        :activeId="currentConversationId"
        @select="selectConversation"
        @new-chat="createNewChat"
        @delete="deleteConversation"
      />
      <div class="chat-container">
        <div class="chat-header">
          <div class="logo">
            <img src="/images.png" alt="Logo Bách Khoa" />
            <div>
              <h2>Trợ lý Học tập</h2>
              <p>Đại học Bách Khoa</p>
            </div>
          </div>
        </div>

        <div class="chatbox" ref="chatbox">
          <div v-if="messages.length === 0" class="empty-state">
            <div class="empty-icon">💬</div>
            <h3>Bắt đầu cuộc trò chuyện</h3>
            <p>Hỏi tôi bất kỳ điều gì về chương trình đào tạo</p>
          </div>
          <div v-for="(msg, index) in messages" :key="index" :class="['message-wrapper', msg.sender]">
            <div class="message-bubble" v-html="renderMarkdown(msg.text)"></div>
          </div>
        </div>

        <div class="input-container">
          <div class="input-area">
            <input
              type="text"
              v-model="userInput"
              @keydown.enter="sendMessage"
              placeholder="Nhập câu hỏi của bạn..."
              class="message-input"
            />
            <button @click="sendMessage" class="send-btn" :disabled="!userInput.trim()">
              <span class="send-icon">➤</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<script>
import MarkdownIt from "markdown-it";
import ChatSidebar from '../components/ChatSidebar.vue'
import api from '@/services/api'

const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true,
});

export default {
    components:{
      ChatSidebar
    },
  data() {
    return {
      userInput: "",
      messages: [],
      conversations:[],
      currentConversationId: null
    };
  },
  methods: {
    renderMarkdown(text) {
      try {
        return md.render(text || "");
      } catch (e) {
        return text ? text.replace(/\n/g, "<br>") : "";
      }
    },
    async sendMessage() {
      const text = this.userInput.trim();
      if (!text) return;

      this.messages.push({ text, sender: "user" });
      this.userInput = "";

      try {
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/chat`,
          {
            method: "POST",
            headers: { 
              "Content-Type": "application/json", 
               Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
            body: JSON.stringify({ 
              message: text,
              conversation_id: this.currentConversationId
            }),
          }
        );
        const data = await res.json();
        
        this.messages.push({ text: data.reply, sender: "bot" });
        
        if(!this.currentConversationId && data.conversation_id){
          this.currentConversationId = data.conversation_id;
          this.loadConversations();
        }

        this.$nextTick(() => {
          this.$refs.chatbox.scrollTop = this.$refs.chatbox.scrollHeight;
        });
      } catch (e) {
        this.messages.push({
          text: "Lỗi kết nối đến máy chủ!",
          sender: "bot",
        });
      }
    },

    async loadConversations() {
      try {
        const res = await api.get('/chat/conversations')
        this.conversations = res.data
      } catch (err) {
        console.error('Lỗi load conversations', err)
        this.conversations = []   
      }
    },

    async selectConversation(id) {
      this.currentConversationId = id;

      try {
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/chat/conversations/${id}/messages`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          }
        );

        const data = await res.json();

        this.messages = data.map((m) => ({
          text: m.content,
          sender: m.role === "assistant" ? "bot" : "user",
        }));

        this.$nextTick(() => {
          this.$refs.chatbox.scrollTop = this.$refs.chatbox.scrollHeight;
        });
      } catch (e) {
        console.error("Lỗi load messages", e);
      }
    },

    createNewChat() {
      this.currentConversationId = null;
      this.messages = [];
    },

    async deleteConversation(conversationId) {
      this.conversations = this.conversations.filter(c => c.id !== conversationId);
      
      if (this.currentConversationId === conversationId) {
        this.createNewChat();
      }
    },
  },

  mounted() {
    this.loadConversations();
  },
};
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.home-wrapper {
  width: 100vw;
  min-height: calc(100vh - 64px); 
  padding-top: 64px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: center;
  align-items: stretch;
}

.chat-layout {
  display: flex;
  width: 100%;
  max-width: 1400px;
  height: calc(100vh - 64px);
  gap: 0;
}

/* Chat Container */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  margin: 12px 12px 12px 0;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

/* Header */
.chat-header {
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo img {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  padding: 4px;
}

.logo h2 {
  margin: 0;
  color: white;
  font-size: 18px;
  font-weight: 600;
}

.logo p {
  margin: 2px 0 0 0;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}

/* Chatbox */
.chatbox {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chatbox::-webkit-scrollbar {
  width: 6px;
}

.chatbox::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.chatbox::-webkit-scrollbar-thumb {
  background: #d0d0d0;
  border-radius: 3px;
}

.chatbox::-webkit-scrollbar-thumb:hover {
  background: #b0b0b0;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #666;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  color: #999;
}

/* Messages */
.message-wrapper {
  display: flex;
  margin-bottom: 8px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.bot {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-wrap: break-word;
  overflow-wrap: break-word;
  font-size: 14px;
}

.message-wrapper.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.message-wrapper.bot .message-bubble {
  background: #e8e8e8;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.message-bubble a {
  color: inherit;
  text-decoration: underline;
}

/* Input Container */
.input-container {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.input-area {
  display: flex;
  gap: 8px;
  align-items: center;
}

.message-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 24px;
  outline: none;
  font-size: 14px;
  background: #f8f9fa;
  transition: all 0.2s;
  font-family: inherit;
}

.message-input:focus {
  background: white;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.message-input::placeholder {
  color: #999;
}

.send-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  font-size: 18px;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-icon {
  display: inline-block;
}

/* Responsive */
@media (max-width: 768px) {
  .chat-layout {
    flex-direction: column;
  }

  .chat-container {
    margin: 12px;
  }

  .message-bubble {
    max-width: 85%;
  }

  .logo h2 {
    font-size: 16px;
  }

  .logo img {
    width: 40px;
    height: 40px;
  }

  .input-area {
    gap: 6px;
  }

  .message-input {
    font-size: 12px;
  }
}</style>
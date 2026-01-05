<template>
  <div class="home-wrapper">
    <div class="chat-layout">
      <ChatSidebar
        :conversations="conversations"
        :activeId="currentConversationId"
        @select="selectConversation"
        @new-chat="createNewChat"
      />  
      <div class="chat-container">
        <div class="logo">
          <img src="/images.png" alt="Logo Bách Khoa" />
          <span><strong>Đại học Bách Khoa</strong></span>
        </div>

        <h1>Hôm nay bạn có thắc mắc gì về chương trình đào tạo ?</h1>

        <div class="chatbox" ref="chatbox">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['message', msg.sender]"
            v-html="renderMarkdown(msg.text)"
          ></div>
        </div>

        <div class="input-area">
          <input
            type="text"
            v-model="userInput"
            @keydown.enter="sendMessage"
            placeholder="Bạn có thắc mắc gì về chương trình đào tạo của trường Đại học Bách Khoa?"
          />
          <button @click="sendMessage">Gửi</button>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import MarkdownIt from "markdown-it";
import ChatSidebar from '../components/ChatSidebar.vue'
import api from '@/services/api'

async function loadConversations() {
  try {
    const res = await api.get('/chat/conversations')
    conversations.value = res.data
  } catch (err) {
    console.error('Lỗi load conversations', err)
    conversations.value = [] // tránh crash UI
  }
}
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
               Authorization: 'Bearer ${localStorage.getItem("access_token")}',
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
    // ===== HISTORY =====

    async  loadConversations() {
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
              Authorization: `Bearer ${localStorage.getItem("token")}`,
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
  },

  mounted() {
    this.loadConversations();
  },
};
</script>

<style scoped>
/* Toàn bộ nền giống Login */
.home-wrapper {
  width: 100vw;
  min-height: calc(100vh - 64px); 
  padding-top: 64px;

  background: rgb(77, 144, 254);
  display: flex;
  justify-content: center;
  /* align-items: center; */
}
.chat-layout {
  display: flex;
  width: 100%;
  max-width: 1200px;
  height: calc(100vh - 64px);
}
/* Khung chat */
.chat-container {
  flex: 1;
  width: 800px;
  max-width: 95%;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 30px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.logo img {
  width: 50px;
  height: 50px;
}

h1 {
  text-align: center;
  margin-bottom: 20px;
  font-size: 20px;
  color: #1a237e;
}

.chatbox {
  width: 100%;
  height: 400px;
  overflow-y: auto;
  border-radius: 8px;
  padding: 12px;
  background-color: #f7f7f7;
  margin-bottom: 15px;
}

.input-area {
  display: flex;
  width: 100%;
  gap: 10px;
}

.input-area input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #ccc;
  border-radius: 8px;
  outline: none;
}

.input-area button {
  background-color: #1a237e;
  color: white;
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.3s;
}

.input-area button:hover {
  background-color: rgb(77, 144, 254);
}

/* Tin nhắn */
.message {
  margin: 8px 0;
  line-height: 1.5;
  white-space: pre-wrap;
}

.message.bot {
  text-align: left;
  color: #000;
}

.message.user {
  text-align: right;
  color: #c6c8e1;
}

</style>

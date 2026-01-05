async function sendMessage() {
  const input = document.getElementById('question');
  const chat = document.getElementById('chat');
  const message = input.value.trim();
  if (!message) return;

  // Hiển thị tin nhắn người dùng
  chat.innerHTML += `<div class="message user">${message}</div>`;
  input.value = '';

  // Gửi đến backend
  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const data = await response.json();
    chat.innerHTML += `<div class="message bot">${data.reply}</div>`;
    chat.scrollTop = chat.scrollHeight;
  } catch (error) {
    chat.innerHTML += `<div class="message bot">Lỗi kết nối đến máy chủ!</div>`;
  }
}

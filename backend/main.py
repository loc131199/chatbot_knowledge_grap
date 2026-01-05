
# main.py

import os
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from neo4j_handle import Neo4jHandler
from openai_handler import GeminiHandler
from chatbot_logic import ChatbotLogic

if __name__ == "__main__":
    # Khởi tạo các handler
    try:
        neo4j_h = Neo4jHandler(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        gemini_h = GeminiHandler() # GeminiHandler tự xử lý cấu hình API Key
    except Exception as e:
        print(f"Lỗi khởi tạo hệ thống: {e}")
        # Nếu có lỗi kết nối hoặc cấu hình, chương trình sẽ thoát
        exit()

    # Khởi tạo logic chatbot
    chatbot = ChatbotLogic(neo4j_h, gemini_h)

    # Hiển thị lời chào và hướng dẫn sử dụng
    print("Chào bạn! Tôi là chatbot thông tin về điều kiện tốt nghiệp và các chương trình đào tạo.")
    print("Bạn có thể hỏi như: 'Điều kiện tốt nghiệp là gì?', 'Thông tin chương trình Công nghệ chế tạo máy là gì?', 'Có những chương trình đào tạo nào?'")
    print("Gõ 'thoát' để kết thúc.")

    # Vòng lặp chính để chatbot liên tục tương tác với người dùng
    while True:
        user_input = input("Bạn: ")
        if user_input.lower() == 'thoát':
            print("Chatbot: Tạm biệt! Hẹn gặp lại.")
            break
        
        bot_response = chatbot.chat(user_input)
        print(f"Chatbot: {bot_response}\n")

    # Đóng kết nối Neo4j khi chương trình kết thúc
    neo4j_h.close()

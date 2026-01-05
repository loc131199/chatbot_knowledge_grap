from backend.chatbot_logic import ChatbotLogic as CoreChatbotLogic
from backend.app.services.openai_service import OpenAIHandler

class ChatbotLogic:
    """
    Wrapper cho ChatbotLogic cũ để dùng trong FastAPI
    """

    def __init__(self):
        self.openai_handler = OpenAIHandler()
        self.core = CoreChatbotLogic()

    def chat(self, message: str) -> str:
        # gọi lại logic cũ
        return self.core.handle_user_query(message)

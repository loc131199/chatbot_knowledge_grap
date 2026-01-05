# backend/logic_chatbot.py
from backend.neo4j_handle import Neo4jHandler
from backend.openai_handler import OpenAIHandler
from backend.intent_detector import IntentDetector


class ChatbotLogic:
    def __init__(self):
        self.neo4j_handle = Neo4jHandler()
        self.openai_handler = OpenAIHandler()
        self.intent_detector = IntentDetector()
        
    def handle_user_query(self, question):
        """
        Phân loại câu hỏi và chọn truy vấn phù hợp.
        Pipeline hiện tại:
        1️⃣ Biến đổi câu hỏi nếu cần
        2️⃣ BM25 search trên Neo4j
        3️⃣ LLM/NLP reasoning trên kết quả BM25
        """
        # 1️⃣ Biến đổi câu hỏi nếu cần
        question_transformed = self.intent_detector.transform_question(question)
        
        # 2️⃣ Xác định intent
        intent = self.intent_detector.detect_intent(question_transformed)
        
        # ---- LOG DEBUG để kiểm tra ----
        print(f"[DEBUG] Intent detected: {intent}")
        print(f"[DEBUG] Transformed question: {question_transformed}")

        # ---- 3️⃣ Xử lý theo intent ----
        if intent == "hoi_dieu_kien_tot_nghiep_chung":
            data = self.neo4j_handle.get_dieu_kien_tot_nghiep_chung()
            return self.openai_handler.summarize_graduation_conditions(data, question_transformed)
        
        elif intent == "hoi_dieu_kien_tot_nghiep_ctdt":
            # question gốc để BM25 tìm đúng CTĐT
            data = self.neo4j_handle.get_dieu_kien_tot_nghiep_ctdt(question)
            if not data:
                return "Xin lỗi, tôi không tìm thấy thông tin về điều kiện tốt nghiệp của chương trình này."
            summarized = self.openai_handler.summarize_graduation_conditions(data, question)
            return summarized
        
        elif intent == "chuan_ngoai_ngu_ctdt":
            # question gốc để BM25 tìm đúng CTĐT
            data = self.neo4j_handle.get_chuan_ngoai_ngu_dau_ra_cua_ctdt(question)
            if not data:
                return "Xin lỗi, tôi không tìm thấy thông tin về chuẩn ngoại ngữ đầu ra của chương trình này."
            summarized = self.openai_handler.summarize_language_requirements_ctdt(data, question)
            return summarized

        elif intent == "hoi_chuan_ngoai_ngu_dau_ra_chung":
            data = self.neo4j_handle.get_chuan_ngoai_ngu_dau_ra_chung()
            return self.openai_handler.summarize_language_requirements(data, question_transformed)
        # 🆕 Intent: hỏi mức điểm/chứng chỉ ngoại ngữ (ví dụ: "IELTS bao nhiêu thì tốt nghiệp?")
        elif intent == "hoi_chuan_ngoai_ngu_muc_diem":
            # Lấy dữ liệu từ Neo4j (dùng fulltext NgoaiNgu_fulltext)
            data = self.neo4j_handle.query_language_requirement(question)

            if not data:
                return "Mình không tìm thấy thông tin về mức điểm/chứng chỉ ngoại ngữ phù hợp cho câu hỏi này."

            # Gửi toàn bộ dữ liệu raw cho OpenAI để nó:
            # - nếu câu hỏi có tên CTĐT: ghép đúng CTĐT và trả chi tiết cho CTĐT đó
            # - nếu câu hỏi chung: tổng hợp mức điểm/chứng chỉ chung
            return self.openai_handler.summarize_language_score_requirement_properties(data, question)
        elif intent == "hoi_khung_nang_luc_ngoai_ngu":
            # 1) Lấy dữ liệu từ Neo4j
            data = self.neo4j_handle.get_khung_nang_luc_ngoai_ngu()

            if not data:
                return "Mình không tìm thấy thông tin về khung năng lực ngoại ngữ."

            # 2) Gửi cho OpenAI để tóm tắt trả lời
            return self.openai_handler.summarize_language_framework(data, question)
        elif intent == "hoi_thong_tin_ctdt":
            # question gốc để BM25 tìm đúng CTĐT
            data = self.neo4j_handle.get_course(question)
            if not data:
                return "Xin lỗi, tôi không tìm thấy thông tin về  chương trình đào tạo này."
            return self.openai_handler.get_course(data,question)
        elif intent == "hoi_danh_sach_ctdt":
            # Lấy danh sách tất cả CTĐT từ Neo4j
            data = self.neo4j_handle.get_list_course()

            if not data:
                return "Xin lỗi, tôi không tìm thấy danh sách chương trình đào tạo nào."

            # Gửi toàn bộ danh sách sang OpenAI để format/trả lời có logic
            return self.openai_handler.get_list_course(data, question_transformed)
        
        elif intent == "hoi_tien_quyet_hoc_phan_ctdt":
            data = self.neo4j_handle.get_tien_quyet(question)

            if not data:
                return (
                    "Mình không tìm thấy quan hệ tiên quyết nào phù hợp với câu hỏi của bạn. "
                    "Có thể tên học phần hoặc chương trình đào tạo chưa chính xác."
                )

            # gửi sang OpenAI để suy luận + trả đúng dạng (4): "Nếu trượt X thì không học được môn nào?"
            return self.openai_handler.get_tien_quyet(data, question)

        elif intent == "hoi_hoc_phan_song_hanh_ctdt":
                    # 1) Lấy dữ liệu song hành từ Neo4j (neo4j_handle.get_song_hanh)
                    data = self.neo4j_handle.get_song_hanh(question)

                    # 2) Nếu không có kết quả → trả thông báo rõ ràng
                    if not data:
                        return (
                            "Mình không tìm thấy quan hệ học phần song hành phù hợp với câu hỏi của bạn. "
                            "Có thể tên học phần hoặc chương trình đào tạo chưa chính xác."
                        )
                    return self.openai_handler.get_song_hanh(data, question)

        else:
            bm25_results = self.neo4j_handle.bm25_search(question_transformed)
            return self.openai_handler.reason_over_results(bm25_results, question_transformed)


# backend/openai_handler.py
from backend.config import client
import json
from collections import OrderedDict

class OpenAIHandler:
    def __init__(self):
        self.client = client  # gán client từ config
        self.model_embedding = "text-embedding-3-small"
        self.model_reasoning = "gpt-4o-mini"

    # ---------- Embedding ----------
    def create_embedding(self, text):
        response = client.embeddings.create(
            model=self.model_embedding,
            input=text
        )
        return response.data[0].embedding

    # ---------- Summarization ----------

    def summarize_graduation_conditions(self, data, question):
        """
        Tổng hợp điều kiện tốt nghiệp (chung hoặc của 1 CTĐT cụ thể),
        bao gồm chi tiết chuẩn ngoại ngữ đầu ra (TOEIC, IELTS, JLPT, DELF, ...),
        dựa trên dữ liệu truy vấn từ Neo4j.
        """
        if not data:
            return "Hiện chưa có dữ liệu điều kiện tốt nghiệp trong hệ thống."

        # Nếu dữ liệu là dict thì chuyển thành list để xử lý thống nhất
        if isinstance(data, dict):
            data = [data]
        # Nếu dữ liệu chỉ là chuỗi (do lỗi hoặc dữ liệu rỗng)
        elif isinstance(data, str):
            return f"Không thể phân tích dữ liệu điều kiện tốt nghiệp: {data}"

        formatted = ""

        for d in data:
            # Bỏ qua nếu không phải dict
            if not isinstance(d, dict):
                continue

            ten_ctdt = d.get("ten_chuong_trinh", "Không rõ tên chương trình")
            dk_chung = d.get("dieu_kien_chung", "Không có thông tin về điều kiện chung.")
            dk_rieng = d.get("dieu_kien_rieng", "")
            ngoai_ngu_list = d.get("ngoai_ngu_list") or d.get("thong_tin_ngoai_ngu", [])

            formatted += f"🎓 **{ten_ctdt}**\n"
            formatted += f"  • Điều kiện chung: {dk_chung.strip()}\n"

            if dk_rieng and dk_rieng.strip() and dk_rieng.lower() != "không có yêu cầu riêng.":
                formatted += f"  • Điều kiện riêng: {dk_rieng.strip()}\n"

            # ---- Chuẩn ngoại ngữ đầu ra chi tiết ----
            if isinstance(ngoai_ngu_list, list) and len(ngoai_ngu_list) > 0:
                formatted += "  • Chuẩn ngoại ngữ đầu ra:\n"
                for item in ngoai_ngu_list:
                    if not isinstance(item, dict):
                        continue

                    lang_type = item.get("lang_type")
                    info = item.get("thong_tin_ngoai_ngu", {})
                    if not info:
                        continue

                    details = []
                    for k, v in info.items():
                        if v and str(v).strip():
                            details.append(f"{k}: {v}")

                    if details:
                        lang_name = (
                            "Tiếng Anh" if lang_type == "TiengAnh"
                            else "Tiếng Nhật" if lang_type == "TiengNhat"
                            else "Tiếng Pháp" if lang_type == "TiengPhap"
                            else lang_type or "Ngôn ngữ khác"
                        )
                        formatted += f"     - {lang_name} → " + ", ".join(details) + "\n"
            else:
                formatted += "  • Không có thông tin cụ thể về chuẩn ngoại ngữ.\n"

            formatted += "\n"

        # ----------------- PROMPT RÕ RÀNG -----------------
        prompt = f"""
        Bạn là trợ lý học vụ của Đại học Bách Khoa.

        Người dùng hỏi: "{question}"

        Dưới đây là dữ liệu lấy từ Neo4j, gồm thông tin chi tiết về điều kiện tốt nghiệp
        và chuẩn ngoại ngữ đầu ra (TOEIC, IELTS, JLPT, DELF, v.v.):

        {formatted}

        Yêu cầu:
        1️⃣ Trả lời rõ ràng, có cấu trúc, dễ hiểu, trả lời đầy đủ không lượt bỏ thông tin của neo4j.
        2️⃣ Nếu có thông tin chi tiết (TOEIC, IELTS, JLPT...), hãy nêu cụ thể theo từng ngôn ngữ.
        3️⃣ Nếu một chương trình có nhiều chuẩn ngoại ngữ (VD: Tiếng Anh + Tiếng Nhật), hãy liệt kê tất cả.
        4️⃣ Không được trả lời mơ hồ kiểu "theo quy định của từng chương trình".
        """

        try:
            response = client.chat.completions.create(
                model=self.model_reasoning,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là trợ lý học vụ thông minh, chuyên trả lời câu hỏi về điều kiện tốt nghiệp. "
                            "Nếu dữ liệu có TOEIC, IELTS, JLPT, DELF... thì phải nêu rõ ràng, không được bỏ qua."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return (
                f"Dưới đây là dữ liệu lấy từ Neo4j (hiển thị đầy đủ, chưa qua GPT):\n\n{formatted}\n\n"
                f"Lỗi: {str(e)}"
            )

    #Hàm toán tắt riêng cho câu hỏi chuẩn ngoại ngữ đầu ra là gì?
    def summarize_language_requirements(self, data, question):
        """
        Tóm tắt thông tin chuẩn ngoại ngữ đầu ra của các chương trình đào tạo.
        """
        # Ghép dữ liệu text từ kết quả truy vấn Neo4j
        text = "Dưới đây là dữ liệu chuẩn ngoại ngữ đầu ra được hệ thống thu thập:\n\n"
        for d in data:
            ten = d.get("ten_chuong_trinh", "Chương trình chưa rõ")
            text += f"- {ten}:\n"
            ngoai_ngu_list = d.get("ngoai_ngu_list", [])
            if not ngoai_ngu_list:
                text += "  • Không có thông tin ngoại ngữ đầu ra.\n"
            else:
                for item in ngoai_ngu_list:
                    lang_type = item.get("lang_type", "Không rõ")
                    details = item.get("thong_tin_ngoai_ngu", {})
                    detail_text = ", ".join(f"{k}: {v}" for k, v in details.items() if v)
                    text += f"  • {lang_type}: {detail_text or 'Không có thông tin cụ thể'}\n"
            text += "\n"

        # Gửi cho GPT tóm tắt lại ngắn gọn, dễ hiểu
        prompt = f"""
Bạn là một trợ lý học vụ của Đại học Bách Khoa.

Người dùng vừa hỏi: "{question}"

Dưới đây là dữ liệu về chuẩn ngoại ngữ đầu ra của các chương trình đào tạo, lấy trực tiếp từ Neo4j (bao gồm tất cả chứng chỉ, bậc yêu cầu, TOEIC, TOEFL, IELTS, Cambridge, JLPT, TOP_J, NAT_TEST, DELF, TCF, v.v.):

{text}

Yêu cầu:
1️⃣ Trả lời rõ ràng, có cấu trúc, dễ hiểu.
2️⃣ Liệt kê **tất cả các loại chứng chỉ và bậc yêu cầu** theo từng ngôn ngữ (Tiếng Anh, Tiếng Nhật, Tiếng Pháp, v.v.).
3️⃣ **Không gộp dữ liệu của các chương trình**, giữ nguyên dữ liệu như trong Neo4j.
4️⃣ Trình bày rõ ràng, dễ đọc.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý học vụ của Đại học Bách Khoa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ Lỗi khi tóm tắt chuẩn ngoại ngữ đầu ra:", e)
            # fallback nếu GPT không phản hồi
            return "Hiện tại hệ thống chưa thể tóm tắt chuẩn ngoại ngữ đầu ra, vui lòng thử lại sau."
    
    def summarize_language_requirements_ctdt(self, data, question):
        """
        Tóm tắt chuẩn ngoại ngữ đầu ra cho MỘT chương trình đào tạo cụ thể.
        Giữ nguyên chi tiết từ Neo4j, chỉ yêu cầu GPT trình bày rõ ràng.
        """
        if not data:
            return "Hiện chưa có dữ liệu về chuẩn ngoại ngữ đầu ra trong hệ thống."

        d = data if isinstance(data, dict) else data[0]
        ten = d.get("ten_chuong_trinh", "Chương trình chưa rõ")
        ngoai_ngu_list = d.get("thong_tin_ngoai_ngu", [])

        # ✅ Format dữ liệu từ Neo4j để GPT hiểu đúng
        text = f"Chương trình đào tạo: {ten}\n\n"
        if not ngoai_ngu_list:
            text += "Không có thông tin cụ thể về chuẩn ngoại ngữ đầu ra."
        else:
            text += "Dữ liệu chuẩn ngoại ngữ đầu ra thu được từ Neo4j:\n"
            for item in ngoai_ngu_list:
                lang_type = item.get("lang_type", "Không rõ")
                details = item.get("thong_tin_ngoai_ngu", {})
                detail_text = ", ".join(f"{k}: {v}" for k, v in details.items() if v)
                text += f"• {lang_type}: {detail_text or 'Không có thông tin cụ thể'}\n"

        # 🧠 Prompt rõ ràng, không cho GPT "bịa"
        prompt = f"""
Bạn là trợ lý học vụ của Đại học Bách Khoa.

Người dùng vừa hỏi: "{question}"

Dưới đây là dữ liệu chuẩn ngoại ngữ đầu ra (lấy trực tiếp từ Neo4j):

{text}

Yêu cầu:
1️⃣ Trả lời **chính xác theo dữ liệu trên**, không tự suy diễn hay giả định.
2️⃣ Giữ nguyên mọi thông tin chứng chỉ, bậc yêu cầu (TOEIC, IELTS, JLPT...).
3️⃣ Trình bày đẹp, dễ đọc, rõ ràng theo từng ngôn ngữ.
4️⃣ Nếu không có dữ liệu, nói rõ "Chưa có thông tin trong hệ thống."
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý học vụ, chỉ trình bày lại dữ liệu từ Neo4j, không suy diễn."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ Lỗi khi tóm tắt chuẩn ngoại ngữ đầu ra CTĐT:", e)
            # fallback hiển thị dữ liệu thô
            return text


    def summarize_language_score_requirement_properties(self, data, question: str):
        """
        Xử lý tất cả chứng chỉ ngoại ngữ cho câu hỏi dạng:
        - TOEIC/IELTS/Cambridge/TOEFL_iBT/TOEFL_ITP/JLPT/NAT_TEST/TOP_J/DELF_va_DALF/TCF
        """
        # chuẩn hóa tên chứng chỉ từ question
        cert_keywords = [
            "toeic","ielts","toefl","cambridge","chung_chi",
            "jlpt","nat_test","top_j","delf","tcf"
        ]
        for cert in cert_keywords:
            if cert in question.lower():
                requested_cert = cert
                break
        else:
            requested_cert = None  # nếu không tìm thấy, gửi tất cả

        prompt = f"""
    Bạn là trợ lý học vụ Đại học Bách Khoa.
    Dữ liệu chuẩn đầu ra ngoại ngữ từ Neo4j:
    {data}

    Câu hỏi: "{question}"

    Yêu cầu:
    - Nếu requested_cert không rỗng, chỉ trả kết quả mức điểm/chứng chỉ của chứng chỉ đó, tổng hợp nếu nhiều CTĐT.
    - Nếu có CTĐT trong câu hỏi, trả mức chứng chỉ của CTĐT đó.
    - Nếu không có CTĐT, trả kết quả tổng hợp chung.
    - Không tự bịa thông tin, chỉ dựa trên dữ liệu.
    - Trình bày gọn gàng, rõ ràng.
    """

        # Gọi LLM
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()


    def summarize_language_framework(self, data, question: str):
        """
        Tóm tắt khung năng lực ngoại ngữ và các bậc/chứng chỉ của từng ngôn ngữ.
        - data: trả về từ get_khung_nang_luc_ngoai_ngu()
        - question: câu hỏi người dùng
        """
 
        prompt = f"""
        Bạn là trợ lý học vụ Đại học Bách Khoa.

        Dữ liệu khung năng lực ngoại ngữ từ Neo4j:
        {data}

        Người dùng hỏi: "{question}"

        Yêu cầu trình bày:
        - Giải thích "khung năng lực ngoại ngữ" là gì dựa trên trường dữ liệu `khai_niem`.
        - Liệt kê chi tiết từng ngôn ngữ theo thứ tự: Tiếng Anh → Tiếng Pháp → Tiếng Nhật → Tiếng Trung.
        - Trong mỗi ngôn ngữ:
            - Nhóm dữ liệu theo `bậc` tăng dần (bậc 1 → bậc 2 → …).
            - Dưới mỗi bậc, liệt kê tất cả chứng chỉ/mức điểm tương ứng (ví dụ TOEIC, IELTS, Cambridge, TOEFL_iBT, TOEFL_ITP đối với Tiếng Anh).
            - Nếu một chứng chỉ không có dữ liệu, bỏ qua.
        - Trình bày gọn gàng, dùng danh sách đầu dòng cho từng chứng chỉ/mức điểm.
        - Không bịa thêm thông tin ngoài dữ liệu.

        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    def get_course(self, data: list, question: str):
        """
        Format dữ liệu CTĐT đã xử lý từ Neo4j (list[dict]).
        - data: list[dict] từ Neo4j
        - question: câu hỏi người dùng
        """

        
        # đảm bảo data là JSON string
        try:
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            data_json = str(data)

        prompt = f"""
    Bạn là trợ lý AI chuyên trả lời câu hỏi về **chương trình đào tạo** dựa trên dữ liệu từ Neo4j.

      **Bạn KHÔNG được bịa dữ liệu.**  
      **Chỉ dùng đúng dữ liệu cung cấp trong JSON dưới đây.**

    Dữ liệu CTĐT từ Neo4j:
    {data_json}

    Câu hỏi người dùng: "{question}"

    ==================================================
    🎯 **QUY TẮC TRẢ LỜI**
    ==================================================
    Luôn trả lời NGẮN GỌN – CHÍNH XÁC – KHÔNG LAN MAN.

    Nếu câu hỏi yêu cầu thông tin chi tiết → trả lời đầy đủ.  
    Nếu câu hỏi chỉ cần 1 phần thông tin → CHỈ trả về phần đó.

    Nếu dữ liệu không tồn tại → ghi **"Không có dữ liệu"**.

    ==================================================
     **PHÂN LOẠI CÂU HỎI & CÁCH TRẢ LỜI**
    ==================================================

    1 **Thông tin tổng quan**
    - Ví dụ:
    - "Chương trình đào tạo A là gì?"
    - "Thông tin về chương trình đào tạo A"
    → Trả về đầy đủ:
    - Tên chương trình
    - Mã
    - Khoa
    - Tổng tín chỉ
    - Nội dung
    - Danh sách học phần theo từng học kỳ
    - Thống kê (nếu có)

    ---

    2 **Hỏi về khoa**
    - "Chương trình đào tạo A thuộc khoa nào?"
    → Chỉ trả lời: **Tên khoa**

    ---

    3 **Danh sách toàn bộ học phần**
    - "Chương trình A gồm những học phần nào?"
    → Trả về toàn bộ danh sách học phần, KHÔNG kèm thông tin khác.

    ---

    4 **Hỏi theo loại học phần**
    Ví dụ:
    - “Những học phần đại cương của chương trình A là gì?”
    - “Những học phần tiên quyết…”
    - “Những học phần tự do…”
    - “Những học phần song hành…”
    - “Chương trình A có những học phần đại cương nào?”
    - “Chương trình A có những học phần tiên quyết nào?”
    - “Chương trình A có những học phần tự do nào?”
    - “Chương trình A có những học phần song hành?”
    → Chỉ trả lời đúng danh sách loại đó.

    ---

    5 **Học phần theo học kỳ**
    - “Những học phần phải học trong học kỳ 3 của chương trình A?”
    → Chỉ trả về danh sách học phần thuộc **học kỳ đó**.

    ---

    6 **Học phần đồ án**
    - “Những học phần đồ án của chương trình đào tạo A?”
    - “Chương trình A có những học phần đồ án nào?”
    → Lọc theo từ khóa:
    - "PBL""

    ---
    ---

    7 **Hỏi loại của một học phần bất kỳ trong chương trình đào tạo  **
    - “Học phần B của chương trình đào tạo A là loại học phần gì?”
    - “Trong chương trình A học phần B là học phần gì?”
    - “Trong chương trình A học phần B là loại học phần gì?”
    → Lọc theo theo tên của học phần B và đưa ra tên loại học phần và số tín chỉ của học phần B
    

    ---

    8 **Không xác định được loại câu hỏi**
    → Trả về đầy đủ như mục (1).


    ==================================================
    🎯 QUY TẮC ĐỊNH DẠNG TRẢ LỜI
    ==================================================
    - Plain text, sạch, dễ đọc.
    - Không nhắc lại yêu cầu.
    - Không thêm lời chúc.
    - Không tự suy diễn ngoài data JSON.

    """

        # chọn model reasoning nếu có
        model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI chuyên format dữ liệu chương trình đào tạo theo yêu cầu người dùng và dựa hoàn toàn vào dữ liệu JSON cung cấp."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    def get_list_course(self, data: list, question: str):
        """
        Format danh sách tất cả chương trình đào tạo để trả lời chatbot.
        """

        
        try:
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            data_json = str(data)

        prompt = f"""
        Bạn là trợ lý AI chuyên trả lời câu hỏi về danh sách chương trình đào tạo.
        Bạn KHÔNG được bịa dữ liệu. Chỉ dùng đúng dữ liệu trong JSON dưới đây.

        Danh sách CTĐT:
        {data_json}

        Câu hỏi người dùng: "{question}"

        -------------------------
        QUY TẮC TRẢ LỜI
        -------------------------
        - Trả lời ngắn gọn, đúng trọng tâm.
        - Chỉ liệt kê danh sách chương trình đào tạo.
        - Với mỗi CTĐT, trả về: 
            • Tên chương trình
            • Mã chương trình (nếu có)
            • Tổng số tín chỉ yêu cầu (nếu có)
        - Không thêm mô tả hoặc thông tin khác.
        - Trả về dạng bullet list dễ đọc.
        - Nếu dữ liệu rỗng → trả về: "Không có dữ liệu".

        -------------------------
        ĐỊNH DẠNG TRẢ LỜI
        -------------------------
        Ví dụ:
        - Tên: Công nghệ thông tin; Mã: 7480201; Tín chỉ: 150
        - Tên: Kỹ thuật cơ khí; Mã: 7520103; Tín chỉ: 145
        """

        model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI chuyên liệt kê danh sách CTĐT."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    def get_tien_quyet(self, data: list, question: str):
        """
        Format dữ liệu tiên quyết từ Neo4j và trả lời câu hỏi liên quan đến tiên quyết.
        - data: list[dict] do neo4j_handle.get_tien_quyet() trả về
        - question: câu hỏi người dùng
        Trả về: plain text short answer (theo quy tắc, hoặc "Không có dữ liệu")
        """

        # đảm bảo data là JSON string để nhét vào prompt
        try:
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            data_json = str(data)

        prompt = f"""
    Bạn là trợ lý AI chuyên trả lời câu hỏi về **quan hệ tiên quyết giữa các học phần**
    trong một chương trình đào tạo, **dựa hoàn toàn** trên dữ liệu JSON từ Neo4j.

    ⭐ **QUY TẮC TUYỆT ĐỐI (bắt buộc):**
    - Chỉ được dùng đúng dữ liệu có trong JSON dưới đây. KHÔNG ĐƯỢC BỊA hoặc SUY DIỄN ngoài dữ liệu.
    - Nếu dữ liệu không đủ để trả lời chính xác → phải trả **"Không có dữ liệu"** (exact).
    - Trả lời NGẮN GỌN, RÕ RÀNG, bằng tiếng Việt.

    Dữ liệu Neo4j (JSON):
    {data_json}

    Câu hỏi người dùng: "{question}"

    =========================================
    🎯 NHỮNG LOẠI CÂU HỎI VÀ CÁCH TRẢ LỜI (bắt buộc theo mẫu)
    =========================================

    1) Liệt kê toàn bộ quan hệ tiên quyết trong một chương trìn đào tạo bất kỳ
    Ví dụ câu hỏi:
        -"trong chương trình công nghệ thông tin Nhật học phần nào là học phần tiên quyết"
        - "Trong chương trình A có những quan hệ tiên quyết nào?"
        - "Danh sách môn tiên quyết trong chương trình A này?"
    Trả ví dụ:
        - "A là tiên quyết của B"
        - "C là tiên quyết của D"
    (Trả mỗi quan hệ trên 1 dòng)

    2) Hỏi tiên quyết của một học phần X (các môn phải học trước X) Trong chương trình đào tạo bất kỳ
    Ví dụ:
        - "Để học Vi xử lý chương trình A cần học trước môn nào?"
        - "Môn Cấu trúc dữ liệu chương trình A có tiên quyết gì không?"
    Nếu có: trả các tên môn (mỗi môn trên 1 dòng) kèm tiền tố ngắn:
        - "Tiên quyết của X: A"
        - "Tiên quyết của X: B"
    Nếu không có → trả **"Học phần X không có tiên quyết"**

    3)Trong chương trình đào tạo bất kỳ môn nào yêu cầu X làm tiên quyết? (X → Z)
    Ví dụ:
        - "Trong chương trình A môn Lập trình C là tiên quyết cho những môn nào?"
        - "Những môn nào trong chương trình A yêu cầu Toán A1 làm tiên quyết?"
    Nếu có: trả danh sách môn (mỗi môn 1 dòng) kèm tiền tố ngắn:
        - "Nếu trượt X, không được học: Z"
        - hoặc "X là tiên quyết của: Z"
    Nếu không có → trả **"Không có môn nào yêu cầu X là tiên quyết"**

    4) Trong chương trình đào tạo bất kỳ nếu trượt học phần X  thì không được học môn nào?
    Ví dụ:
        - "Trong chương trình A nếu tôi trượt Vi điều khiển thì không được học môn nào?"
        - "Trong chương trình A thi rớt Giải tích 1 thì bị cấm học những môn gì?"
    Xử lý giống mục (3): trả dạng:
        - "Trong chương trình <tên CTĐT> bạn sẽ không được học: Z1, Z2"
        (hoặc mỗi môn 1 dòng, nhưng cố gắng ngắn gọn 1 dòng nếu ít môn)
    Nếu không có dữ liệu → "Không có dữ liệu"

    5) Hỏi quan hệ tiên quyết giữa hai học phần (C vs B) trong một chương trình đào tạo bất kỳ
    Ví dụ:
        - "Trong chương trình A C có phải tiên quyết của B không?"
        - "Giữa Đại số và Giải tích trong chương trình A thì môn nào là tiên quyết?"
    Nếu có quan hệ trực tiếp A → B → trả:
        - "A là tiên quyết của B"
    Nếu có quan hệ ngược B → A → trả:
        - "B là tiên quyết của A"
    Nếu không có quan hệ trực tiếp → trả:
        - "Không tồn tại quan hệ tiên quyết giữa hai học phần này"

    =========================================
    📌 LƯU Ý KĨ THUẬT
    - Plain text, sạch, dễ đọc.
    - Không in JSON lại, không giải thích cách tìm.
    - Nếu tên học phần xuất hiện nhiều lần trong dữ liệu, chỉ liệt kê các tên không trùng (DISTINCT).
    - Nếu dữ liệu chứa tên CTĐT, bạn có thể đưa tên CTĐT trong câu trả lời khi phù hợp (ví dụ mục 4).
    - Luôn trả ngắn gọn, đúng trọng tâm.   
    Bắt đầu trả lời:
    """

        # chọn model reasoning nếu có
        model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý AI chuyên format trả lời về quan hệ tiên quyết giữa học phần; chỉ dùng dữ liệu JSON cung cấp; không được bịa."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()


    def get_song_hanh(self, data: list, question: str):

        try:
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            data_json = str(data)

        prompt = f"""
    Bạn là trợ lý AI chuyên phân tích **quan hệ học phần song hành** trong CTĐT,
    và bạn CHỈ ĐƯỢC sử dụng dữ liệu JSON dưới đây (không được bịa).

    ⭐⭐ QUY TẮC BẮT BUỘC ⭐⭐
    - Chỉ dùng đúng dữ liệu trong JSON.
    - Nếu không có dữ liệu phù hợp → trả “Không có dữ liệu”.
    - Trả lời ngắn, rõ, đúng trọng tâm.
    - Dùng đúng tên học phần trong JSON.
    - Không in lại JSON.

    ===========================================================
    📌 DỮ LIỆU JSON TỪ NEO4J:
    {data_json}

    📌 CÂU HỎI NGƯỜI DÙNG: "{question}"
    ===========================================================

    🎯 DẠNG CÂU HỎI PHẢI XỬ LÝ
    ===========================================================

    1) **Liệt kê toàn bộ quan hệ song hành**
    Ví dụ:
    - "Trong CTĐT A có những quan hệ song hành nào?"
    → Trả:
    - "A là học phần song hành với B"

    -----------------------------------------------------------

    2) **Hỏi song hành của một học phần X**
    Ví dụ:
    - "Trong CTĐT A môn X song hành với môn nào?"
    -"Học phần nào có mối quan hệ song hành với môn X trong CTĐT A"
    -"Trong CTĐT A học phần nào có thể học cùng lúc với môn X"
    → Nếu hp1 = X → hp2 hoặc hp2 = X → hp1:
        - "Song hành của X là Y"
    → Nếu không có:
        - "Học phần X không có học phần song hành"

    -----------------------------------------------------------

    3) **Hỏi hai môn có thể học cùng lúc không?**
    Ví dụ:
    - "Tôi có thể học A và B cùng lúc trong chương trình C không?"
    - "Trong chương trình C A và B có phải song hành không?"

    Nếu A ↔ B xuất hiện trong JSON:

        ⚠ Lưu ý:
        Trong JSON mới:
        - Tiên quyết của A nằm trong trường:  tien_quyet_hp1  (kiểu: list)
        - Tiên quyết của B nằm trong trường:  tien_quyet_hp2  (kiểu: list)

        • Nếu A và B đều **không có tiên quyết**:
            → "Có, A và B là học phần song hành và đều không có học phần tiên quyết. Bạn có thể học cùng lúc."

        • Nếu A có tiên quyết, B không có:
            → "A và B là học phần song hành, nhưng để học A bạn cần hoàn thành: <danh_sách_tiên_quyết_A>. Sau đó có thể học song hành."

        • Nếu B có tiên quyết, A không có:
            → "A và B là học phần song hành, nhưng để học B bạn cần hoàn thành: <danh_sách_tiên_quyết_B>. Sau đó có thể học song hành."

        • Nếu cả A và B đều có tiên quyết:
            → "A và B là học phần song hành, nhưng bạn phải hoàn thành tiên quyết trước:
                - Tiên quyết của A: ...
                - Tiên quyết của B: ...
            Sau khi hoàn thành mới được học song hành."

    Nếu **không phải song hành**:
    → "Bạn không thể học A và B cùng lúc vì hai học phần này không phải là học phần song hành."

    -----------------------------------------------------------

    4) **Liệt kê các cặp học phần song hành**
    Ví dụ:
    - "Các môn song hành trong chương trình C?"
    → Trả:
    - "A ↔ B"

    -----------------------------------------------------------

    5) **Kiểm tra trực tiếp A có song hành với B không**
    Ví dụ:
    - "Trong chương trình A X có phải song hành của Y không?"
    → Nếu X ↔ Y tồn tại:
        - "Có, X là học phần song hành với Y"
    → Nếu không:
        - "Không tồn tại quan hệ song hành giữa hai học phần này"

    ===========================================================
    📌 LƯU Ý QUAN TRỌNG
    - Tiên quyết là danh sách (list). Nếu list rỗng = không có tiên quyết.
    - Không giải thích quy trình suy luận.
    - Chỉ trả lời dựa trên JSON.

    Bắt đầu trả lời:
    """

        model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý AI chuyên phân tích quan hệ học phần SONG HÀNH. "
                        "Bạn chỉ được dùng dữ liệu JSON, không được tự suy diễn."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()



    # ---------- Reasoning ----------
    def reason_over_results(self, search_results, question):
        """
        Dùng GPT để tổng hợp kết quả từ BM25 + Vector Search.
        """
        if not search_results:
            return "Không tìm thấy thông tin phù hợp với câu hỏi."

        context = "\n".join([f"- {r.get('ten', '')}: {r.get('noi_dung', '')}" for r in search_results])
        prompt = f"""
Người dùng hỏi: "{question}"

Dưới đây là các kết quả tìm kiếm liên quan:
{context}

Hãy viết câu trả lời ngắn gọn, tự nhiên, rõ ràng và chính xác bằng tiếng Việt.
"""

        response = client.chat.completions.create(
            model=self.model_reasoning,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý thông minh giúp trả lời câu hỏi học vụ."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()


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
    def summarize_graduation_conditions_chung(self, data, question):

        if not data:
            return "Hiện chưa có dữ liệu điều kiện tốt nghiệp trong hệ thống."

        if isinstance(data, dict):
            data = [data]

        # -------- Điều kiện chung --------
        dieu_kien_chung = None
        for d in data:
            if d.get("dieu_kien_chung"):
                dieu_kien_chung = d["dieu_kien_chung"]
                break

        # -------- Chuẩn ngoại ngữ theo hệ --------
        he_map = {}

        for d in data:
            for item in d.get("ngoai_ngu_list", []):
                he = item.get("he")
                lang = item.get("lang_type")
                info = item.get("thong_tin_ngoai_ngu", {})

                if not he or not info:
                    continue

                if he not in he_map:
                    he_map[he] = {}

                if lang not in he_map[he]:
                    he_map[he][lang] = info

        # -------- Chương trình có điều kiện riêng --------
        ct_dieu_kien_rieng = []

        for d in data:
            dk_rieng = d.get("dieu_kien_rieng")
            if dk_rieng and dk_rieng.lower() != "không có yêu cầu riêng.":
                ct_dieu_kien_rieng.append({
                    "ten": d.get("ten_chuong_trinh"),
                    "dieu_kien_rieng": dk_rieng
                })

        # -------- FORMAT --------
        formatted = "🎓 **Điều kiện tốt nghiệp chung tại Đại học Bách Khoa**\n\n"

        formatted += "### 1. Điều kiện chung:\n"
        formatted += dieu_kien_chung + "\n\n"

        formatted += "### 2. Chuẩn ngoại ngữ đầu ra:\n\n"

        for he in ["Cử nhân", "Kỹ sư"]:
            if he not in he_map:
                continue

            formatted += f"**Hệ {he}:**\n"

            for lang_type, info in he_map[he].items():
                lang_name = (
                    "Tiếng Anh" if lang_type == "TiengAnh"
                    else "Tiếng Nhật" if lang_type == "TiengNhat"
                    else "Tiếng Pháp" if lang_type == "TiengPhap"
                    else lang_type
                )

                formatted += f"- {lang_name}:\n"
                for k, v in info.items():
                    if v:
                        formatted += f"   • {k}: {v}\n"

            formatted += "\n"

        if ct_dieu_kien_rieng:
            formatted += "### 3. Các chương trình có điều kiện riêng:\n\n"
            for ct in ct_dieu_kien_rieng:
                formatted += f"- **{ct['ten']}**: {ct['dieu_kien_rieng']}\n"

            formatted += "\n"

        # -------- PROMPT GPT --------
        prompt = f"""
        Người dùng hỏi: "{question}"

        Dữ liệu điều kiện tốt nghiệp chung:

        {formatted}

        Yêu cầu:
        - Trình bày đúng cấu trúc học vụ.
        - Chuẩn ngoại ngữ phải xuống dòng từng chứng chỉ.
        - Chỉ nêu tên chương trình khi có điều kiện riêng.
        - Không lặp điều kiện chung.
        - Văn phong ngắn gọn, rõ ràng.
        """

        try:
            response = client.chat.completions.create(
                model=self.model_reasoning,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý học vụ, trả lời điều kiện tốt nghiệp chung chuẩn học thuật."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return formatted + f"\n\nLỗi GPT: {str(e)}"
        
    #Hàm hỏi về điều kiện tốt nghiệp riêng của 1 chương trình cụ thể?
    def summarize_graduation_conditions_ctdt(self, data: dict, question: str):

        if not data:
            return "Xin lỗi, tôi không tìm thấy thông tin điều kiện tốt nghiệp cho chương trình đào tạo này."

        prompt = f"""
    Bạn là trợ lý học vụ Đại học Bách Khoa.

    Hãy trình bày điều kiện tốt nghiệp của chương trình đào tạo sau theo bố cục:

    1. Điều kiện chung.
    2. Điều kiện riêng.
    3. Chuẩn ngoại ngữ đầu ra hệ Cử nhân.
    4. Chuẩn ngoại ngữ đầu ra hệ Kỹ sư.

    Yêu cầu:
    - Trình bày rõ ràng, gạch đầu dòng.
    - Mỗi chứng chỉ xuống dòng riêng.
    - Nếu phần nào không có thì ghi: Không có yêu cầu riêng.

    Dữ liệu:
    {data}

    Câu hỏi: {question}
    """

        response = self.client.chat.completions.create(
            model=self.model_reasoning,   
            messages=[
                {"role": "system", "content": "Bạn là trợ lý học vụ."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()


    #Hàm toán tắt riêng cho câu hỏi chuẩn ngoại ngữ đầu ra là gì?
    def summarize_language_requirements(self, data, question):

        cu_nhan = []
        ky_su = []
        rieng = {}

        for d in data:
            ten = d.get("ten_chuong_trinh", "")

            # --- CỬ NHÂN CHỈ LẤY TIẾNG ANH ---
            for x in d.get("chuan_ngoai_ngu_cu_nhan", []):
                if x["lang_type"] == "TiengAnh":
                    cu_nhan.append(x)

            # --- KỸ SƯ CHỈ LẤY TIẾNG ANH ---
            for x in d.get("chuan_ngoai_ngu_ky_su", []):
                if x["lang_type"] == "TiengAnh":
                    ky_su.append(x)

            # --- NGOẠI NGỮ RIÊNG ---
            if "Nhật" in ten:
                rieng[ten] = [x for x in d.get("chuan_ngoai_ngu_cu_nhan", []) if x["lang_type"] == "TiengNhat"]

            if "PFIEV" in ten or "Pháp" in ten:
                rieng[ten] = [x for x in d.get("chuan_ngoai_ngu_cu_nhan", []) if x["lang_type"] == "TiengPhap"]

        def build_lang_text(items):
            t = ""
            for x in items:
                details = ", ".join(f"{k}: {v}" for k,v in x["thong_tin_ngoai_ngu"].items() if v)
                t += f"• {details}\n"
            return t

        text = "Chuẩn ngoại ngữ đầu ra:\n\n"

        text += "Hệ Cử nhân:\n\nTiếng Anh:\n"
        text += build_lang_text(cu_nhan)

        text += "\nHệ Kỹ sư:\n\nTiếng Anh:\n"
        text += build_lang_text(ky_su)

        text += "\nCác chương trình có ngoại ngữ riêng:\n\n"
        for k,v in rieng.items():
            text += f"{k}:\n"
            for x in v:
                details = ", ".join(f"{k2}: {v2}" for k2,v2 in x["thong_tin_ngoai_ngu"].items() if v2)
                text += f"• {details}\n"
            text += "\n"

        prompt = f"""
    Bạn chỉ cần trình bày lại đúng nội dung sau theo văn phong học vụ,
    KHÔNG thêm, KHÔNG suy diễn, KHÔNG gộp.

    {text}
    """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý học vụ Đại học Bách Khoa."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()
        

    #àm toán tắt riêng cho câu hỏi chuẩn ngoại ngữ đầu ra của 1 học phần cụ thể là gì?
    def summarize_language_requirements_ctdt(self, data, question):

        if not data or not data.get("ten_chuong_trinh"):
            return "Hiện tại tôi chưa tìm thấy thông tin chuẩn ngoại ngữ đầu ra cho chương trình đào tạo bạn hỏi."

        ten = data.get("ten_chuong_trinh", "")
        cu_nhan = data.get("chuan_ngoai_ngu_cu_nhan", [])
        ky_su = data.get("chuan_ngoai_ngu_ky_su", [])

        cu_nhan_anh = [x for x in cu_nhan if x["lang_type"] == "TiengAnh"]
        ky_su_anh = [x for x in ky_su if x["lang_type"] == "TiengAnh"]

        rieng = []

        if "Nhật" in ten:
            rieng = [x for x in cu_nhan if x["lang_type"] == "TiengNhat"]

        if "PFIEV" in ten or "Pháp" in ten:
            rieng = [x for x in cu_nhan if x["lang_type"] == "TiengPhap"]

        def build_lang_text(items):
            t = ""
            for x in items:
                details = ", ".join(
                    f"{k}: {v}" for k, v in x["thong_tin_ngoai_ngu"].items() if v
                )
                t += f"• {details}\n"
            return t

        text = f"Chuẩn ngoại ngữ đầu ra của chương trình {ten}:\n\n"

        text += "Hệ Cử nhân:\n\nTiếng Anh:\n"
        text += build_lang_text(cu_nhan_anh) if cu_nhan_anh else "• Chưa có dữ liệu\n"

        text += "\nHệ Kỹ sư:\n\nTiếng Anh:\n"
        text += build_lang_text(ky_su_anh) if ky_su_anh else "• Chưa có dữ liệu\n"

        if rieng:
            text += "\nNgoại ngữ riêng của chương trình:\n"
            for x in rieng:
                details = ", ".join(
                    f"{k}: {v}" for k, v in x["thong_tin_ngoai_ngu"].items() if v
                )
                text += f"• {details}\n"

        prompt = f"""
        Bạn là trợ lý học vụ đại học.

        Nhiệm vụ:
        Trình bày lại nội dung sau theo văn phong học vụ, rõ ràng, mạch lạc, dễ đọc.

        QUY TẮC BẮT BUỘC:
        - KHÔNG thêm thông tin
        - KHÔNG suy diễn
        - KHÔNG gộp dữ liệu giữa các hệ
        - KHÔNG thay đổi giá trị
        - KHÔNG nhận xét
        - KHÔNG giải thích
        - KHÔNG dùng emoji
        - Giữ nguyên đầy đủ nội dung

        CÁCH TRÌNH BÀY:
        - Tiêu đề in đậm
        - Mỗi hệ đào tạo xuống dòng riêng
        - Mỗi ngoại ngữ có tiêu đề riêng
        - Các tiêu chí trình bày dạng gạch đầu dòng
        - Nếu không có dữ liệu, ghi đúng: "Chưa có dữ liệu"

        Nội dung gốc cần trình bày lại:

        {text}

        Chỉ trả về nội dung đã trình bày, không kèm giải thích.
    """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý học vụ Đại học Bách Khoa."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    def summarize_language_score_requirement_properties(self, data, question: str):
        """
        Xử lý tất cả chứng chỉ ngoại ngữ cho câu hỏi dạng:
        - TOEIC/IELTS/Cambridge/TOEFL_iBT/TOEFL_ITP/JLPT/NAT_TEST/TOP_J/DELF_va_DALF/TCF
        """
        cert_keywords = [
            "toeic","ielts","toefl","cambridge","chung_chi",
            "jlpt","nat_test","top_j","delf","tcf"
        ]
        for cert in cert_keywords:
            if cert in question.lower():
                requested_cert = cert
                break
        else:
            requested_cert = None

        prompt = f"""
    Bạn là trợ lý học vụ Đại học Bách Khoa.

    Dữ liệu chuẩn đầu ra ngoại ngữ từ hệ thống:
    {data}

    Câu hỏi:
    "{question}"

    Yêu cầu:

    1. Chỉ sử dụng dữ liệu đã cho, KHÔNG suy diễn, KHÔNG bổ sung thông tin ngoài dữ liệu.

    2. Câu hỏi đang hỏi về mức điểm chứng chỉ để tốt nghiệp, vì vậy cần tổng hợp theo:
    - Hệ đào tạo (Cử nhân / Kỹ sư).

    3. Nếu nhiều chương trình có cùng mức điểm trong cùng một hệ, hãy gộp thành một mức chung, KHÔNG liệt kê từng chương trình.

    4. Chỉ liệt kê riêng từng chương trình đào tạo nếu:
    - Mức điểm của chương trình đó khác với phần còn lại trong cùng hệ.

    5. Trình bày bằng văn phong học vụ, tự nhiên, mạch lạc, phù hợp để trả lời sinh viên.
    Không trình bày dạng bảng kỹ thuật.

    6. Cấu trúc trình bày bắt buộc theo dạng:

    Chuẩn ngoại ngữ đầu ra:

    Đối với hệ Cử nhân, sinh viên cần đạt:
    - TOEIC: ...

    Đối với hệ Kỹ sư, sinh viên cần đạt:
    - TOEIC: ...

    (Nếu có chương trình đặc thù, trình bày thêm mục riêng bên dưới)

    7. Không nhắc lại dữ liệu thô, không giải thích quy trình xử lý.

    Chỉ trả về phần câu trả lời dành cho sinh viên.

    """

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
    - "trong chương trình đào tạo A những học phần nào là học phần đồ án?"
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
        - "Trong chương trình A học phần tiên quyết của lập trình hướng đối tượng là gì?"
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
    -"Học phần nào có mối quan hệ song hành với môn X trong CTĐT A?"
    -"Trong CTĐT A học phần nào có thể học cùng lúc với môn X?"
    -"trong CTĐT A tôi có thể học môn X cùng lúc với Y được không?"
   
     → Nếu hp1 = X → hp2 hoặc hp2 = X → hp1:
        - "Song hành của X là Y"
    → Nếu không có:
        - "Học phần X không có học phần song hành"

    -----------------------------------------------------------

    3) **Hỏi hai môn có thể học cùng lúc không?**
    Ví dụ:
    - "Tôi có thể học A và B cùng lúc trong chương trình C không?"
    - "Trong chương trình C A và B có phải song hành không?"
    - "Trong chương trình C tôi có thể học A và B cùng lúc được không?"

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

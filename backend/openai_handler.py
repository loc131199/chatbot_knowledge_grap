
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

        # -------- Quyết định --------
        quyet_dinh = None
        for d in data:
            if d.get("Quyet_dinh"):
                quyet_dinh = d["Quyet_dinh"]
                break

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

        if quyet_dinh:
            formatted += f"**Căn cứ theo:** {quyet_dinh}\n\n"

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
        - Giữ nguyên thông tin quyết định.
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

    Hãy trình bày điều kiện tốt nghiệp của chương trình đào tạo theo văn phong học vụ, đúng dữ liệu đã cho.

    Bố cục bắt buộc:

    📌 Quyết định áp dụng:
    - Trích dẫn đầy đủ số quyết định và ngày ban hành (nếu có).

    1. Điều kiện chung.
    2. Điều kiện riêng.
    3. Chuẩn ngoại ngữ đầu ra hệ Cử nhân.
    4. Chuẩn ngoại ngữ đầu ra hệ Kỹ sư.

    Quy tắc trình bày:
    - Chỉ sử dụng dữ liệu đã cho, KHÔNG suy diễn.
    - Mỗi chứng chỉ ngoại ngữ xuống dòng riêng.
    - Nếu một mục không có dữ liệu thì ghi đúng: "Không có yêu cầu riêng."
    - Văn phong học vụ, ngắn gọn, rõ ràng.
    - Không lặp lại dữ liệu.
    - Không thêm thông tin ngoài dữ liệu.

    Dữ liệu:
    {data}

    Câu hỏi:
    {question}

    Chỉ trả về nội dung câu trả lời cho sinh viên.
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

        try:
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            data_json = str(data)

        prompt = f"""
        Bạn là trợ lý AI tư vấn chương trình đào tạo cho sinh viên.

        Bạn chỉ được sử dụng dữ liệu trong JSON dưới đây, tuyệt đối không được suy đoán hay bịa thông tin.

        ========================
        DỮ LIỆU NEO4J
        ========================
        {data_json}

        ========================
        CÂU HỎI NGƯỜI DÙNG
        ========================
        "{question}"

        ========================
        CÁCH TRẢ LỜI
        ========================

        Hãy trả lời bằng văn phong tự nhiên, dễ hiểu, giống người tư vấn.

        Không liệt kê máy móc theo dạng JSON hay key:value.

        Không nhắc lại câu hỏi.

        Không thêm lời chào.

        ========================
        CÁC LOẠI CÂU HỎI
        ========================

        1. Nếu hỏi chương trình thuộc khoa nào  
        → Trả lời ngắn gọn bằng 1 câu.

        ---

        2. Nếu hỏi về tín chỉ  

        Hãy phân biệt rõ:
        - Tổng số tín chỉ
        - Tín chỉ bắt buộc
        - Tín chỉ tự chọn  

        Luôn tách theo:
        - Hệ Cử nhân
        - Hệ Kỹ sư  

        Khi trả lời, hãy diễn đạt thành đoạn văn tự nhiên, mạch lạc như người tư vấn học tập, 
        không liệt kê khô khan theo dạng báo cáo.

        Nếu người dùng chỉ hỏi một hệ → chỉ trả lời hệ đó.  
        Nếu không nói rõ hệ → trả lời cả hai.
        ---

        3. Nếu hỏi về các học phần ví dụ như: "Chương trình đào tạo A có những học phần nào?"  

        Luôn hiểu rằng:
        - Hệ Cử nhân là chương trình chuẩn.
        - Hệ Kỹ sư là chương trình mở rộng, có thêm học phần so với hệ Cử nhân.

        Cách trình bày:

        Hệ Cử nhân gồm các học phần:

        - <Tên học phần> | <Loại học phần> | <Số tín chỉ> tín chỉ
        (lặp cho toàn bộ danh sách, không được bỏ sót)

        Hệ Kỹ sư học thêm các học phần:

        - <Tên học phần> | <Loại học phần> | <Số tín chỉ> tín chỉ
        (lặp cho toàn bộ danh sách học phần thuộc hệ Kỹ sư)

        Không được dùng câu "Hệ Kỹ sư gồm các học phần" nếu hệ Kỹ sư là chương trình mở rộng.

        Không được bỏ học phần nào có trong dữ liệu.

        ---
        4. Nếu hỏi theo loại học phần cụ thể  

        Bao gồm các câu hỏi:

        - Học phần đồ án → lọc các học phần có tên bắt đầu bằng "PBL"
        - Học phần đại cương → lọc theo loai = HocPhanDaiCuong
        - Học phần tự do → lọc theo loai = HocPhanTuDo
        - Học phần kế tiếp → lọc theo loai = HocPhanKeTiep

        → Trả lời giống định dạng câu (3):

        Tên học phần | Loại học phần | Số tín chỉ  

        Và luôn tách theo:
        - Hệ Cử nhân
        - Hệ Kỹ sư  

        Nếu không có → ghi rõ: "Hiện chưa có học phần thuộc loại này trong chương trình."

        ---
    
        5. Nếu hỏi: "Chương trình đào tạo A là chương trình gì"  

        → Trả lời đầy đủ toàn bộ thông tin chương trình, gồm:

        - Tên chương trình
        - Khoa
        - Mô tả chương trình (từ dữ liệu)

        Với từng hệ đào tạo:

        Hệ Cử nhân:
        - Tổng số tín chỉ
        - Tín chỉ bắt buộc
        - Tín chỉ tự chọn
        - Danh sách toàn bộ học phần (mỗi học phần 1 dòng theo mẫu)

        Hệ Kỹ sư:
        - Tổng số tín chỉ
        - Tín chỉ bắt buộc
        - Tín chỉ tự chọn
        - Danh sách các học phần học thêm

        ---

        6. Nếu câu hỏi không rõ loại  
        → Tóm tắt ngắn gọn toàn bộ chương trình.
            
        ========================
        LƯU Ý DIỄN ĐẠT:
        ========================
        Các cách hỏi sau được xem là tương đương nhau:

        - "Công nghệ thông tin Nhật ..."
        - "Chương trình Công nghệ thông tin Nhật ..."
        - "Chương trình đào tạo Công nghệ thông tin Nhật ..."
        - "Trong chương trình đào tạo Công nghệ thông tin Nhật ..."

        Tất cả đều được hiểu là hỏi về cùng một chương trình đào tạo.

        Không được vì khác cách diễn đạt mà kết luận là không có dữ liệu.        
        ========================
        QUY TẮC
        ========================

        - Nếu dữ liệu không có → ghi: "Hiện chưa có dữ liệu."
        - Không bịa.
        - Không suy luận ngoài JSON.
        - Không được rút gọn danh sách học phần.
        - Văn phong tự nhiên, thân thiện, đúng trọng tâm.
        """


        model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là trợ lý tư vấn chương trình đào tạo đại học, trả lời tự nhiên, chính xác dựa trên dữ liệu Neo4j."
                },
                {
                    "role": "user",
                    "content": prompt
                }
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
        - Trả lời tự nhiên và thân thiện với người dùng
        - Liệt kê danh sách chương trình đào tạo.
        - Với mỗi CTĐT, trả về: 
            • Tên chương trình
            • Mã chương trình 
            • Khóa 
             Hãy phân biệt rõ:
            • Tổng số tín chỉ yêu cầu với hệ kỹ sư
            • Tín chỉ bắt buộc với hệ kỹ sư
            • Tín chỉ tự chọn với hệ kỹ sư
            • Tổng số tín chỉ yêu cầu với hệ cữ nhân
            • Tín chỉ bắt buộc với hệ cữ nhân
            • Tín chỉ tự chọn với hệ cữ nhân
        - Không thêm mô tả hoặc thông tin khác.
        - Trả về dạng bullet list dễ đọc.
        - Nếu dữ liệu rỗng → trả về: "Không có dữ liệu".

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

    def get_hoc_phan_theo_hoc_ky_ctdt(self, question: str, data: dict):

        danh_sach = data.get("danh_sach_hoc_phan", [])
        ten_ctdt = data.get("ten_chuong_trinh", "")

        if not danh_sach:
            return "Xin lỗi, tôi không tìm thấy học phần phù hợp với chương trình đào tạo này."

        prompt = f"""
    Bạn là trợ lý học vụ đại học.

    Dữ liệu học phần của chương trình đào tạo "{ten_ctdt}":

    {danh_sach}

    =================================
    CÂU HỎI
    =================================
    "{question}"

    =================================
    QUY TẮC TRẢ LỜI
    =================================

    ### Trường hợp 1:
    Nếu trong câu hỏi có nhắc đến học kỳ cụ thể:
    → Chỉ trả lời các học phần thuộc học kỳ đó.

    ### Trường hợp 2:
    Nếu KHÔNG nhắc học kỳ:
    → Trình bày học phần theo từng học kỳ, nhóm rõ ràng theo học kỳ.

    =================================
    LƯU Ý DIỄN ĐẠT
    =================================

    Các cách hỏi sau được xem là tương đương nhau:

    - "Công nghệ thông tin Nhật ..."
    - "Chương trình Công nghệ thông tin Nhật ..."
    - "Chương trình đào tạo Công nghệ thông tin Nhật ..."
    - "Trong chương trình đào tạo Công nghệ thông tin Nhật ..."

    Tất cả đều được hiểu là hỏi về cùng một chương trình đào tạo.

    Không được vì khác cách diễn đạt mà kết luận là không có dữ liệu.

    =================================
    RÀNG BUỘC BẮT BUỘC
    =================================

    - Chỉ sử dụng dữ liệu đã cho.
    - Không được suy đoán.
    - Không thêm học phần ngoài danh sách.
    - Không nhắc lại câu hỏi.
    - Không giải thích.
    - Không nhận xét.

    =================================
    ĐỊNH DẠNG TRÌNH BÀY
    =================================

    Tên học phần | Mã học phần | Số tín chỉ

    Mỗi học phần một dòng.

    Nếu trình bày nhiều học kỳ, mỗi học kỳ có tiêu đề:

    Học kỳ X:
    ---------------------------------
    """

        try:
            model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý tư vấn chương trình đào tạo đại học, trả lời chính xác dựa trên dữ liệu Neo4j."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ Lỗi GPT:", e)
            return "Xin lỗi, hệ thống gặp lỗi khi xử lý câu hỏi."

    def get_tien_quyet(self, question: str, data: dict):

        danh_sach = data.get("danh_sach_tien_quyet", [])
        ten_ctdt = data.get("ten_chuong_trinh", "")

        if not danh_sach:
            return "Xin lỗi, tôi không tìm thấy thông tin học phần tiên quyết cho chương trình đào tạo này."

        prompt = f"""
    Bạn là trợ lý học vụ đại học.

    Dữ liệu học phần tiên quyết của chương trình đào tạo "{ten_ctdt}":

    {danh_sach}

    =================================
    CÂU HỎI
    =================================
    "{question}"

    =================================
    QUY TẮC HIỂU DỮ LIỆU
    =================================

    Mỗi phần tử trong dữ liệu có dạng:

    - hoc_phan_tien_quyet: học phần A
    - hoc_phan_bi_tien_quyet: học phần B
    - quan_he: "là học phần tiên quyết của"
    → hiểu là: A là học phần tiên quyết của B

    - loai_hoc_phan_cua_hoc_phan_tien_quyet:
    nếu chứa "HocPhanTienQuyet" thì học phần đó là học phần tiên quyết chính thức của chương trình đào tạo

    =================================
    CÁC TRƯỜNG HỢP CẦN TRẢ LỜI
    =================================

    ### Trường hợp 1
    Câu hỏi dạng:
    - "Chương trình đào tạo A có những học phần tiên quyết nào?"
    - "Trong CTĐT A học phần nào là học phần tiên quyết?"

    -> PHẢI liệt kê **TẤT CẢ** học phần thỏa mãn:
    - "loai_hoc_phan_cua_hoc_phan_tien_quyet" = HocPhanTienQuyet
    - KHÔNG được bỏ sót
    - KHÔNG được chọn đại diện
    ---

    ### Trường hợp 2:
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A để học môn X cần học trước môn nào?"
    - "Trong chương trình đào tạo A học phần tiên quyết của học phần X là gì?"
    - "Trong chương trình đào tạo A học phần X có tiên quyết gì không?"

    QUY TẮC DIỄN GIẢI BẮT BUỘC:

    - Học phần X trong câu hỏi LUÔN LUÔN là "hoc_phan_bi_tien_quyet".
    - Các học phần cần học trước X LUÔN LUÔN là các "hoc_phan_tien_quyet".
    - TUYỆT ĐỐI KHÔNG được đảo ngược vai trò hai học phần này.

    CÁCH TRẢ LỜI:

    - Nếu KHÔNG tồn tại học phần X trong cột "hoc_phan_bi_tien_quyet":
    → Trả lời đúng 1 câu:
    "Không có học phần X trong chương trình đào tạo {ten_ctdt}."

    - Nếu CÓ:
    → Trả lời theo mẫu BẮT BUỘC:

    "Để học môn \"X\" trong chương trình đào tạo {ten_ctdt}, bạn cần học trước các học phần sau:"

    Sau đó liệt kê TẤT CẢ học phần trong cột "hoc_phan_tien_quyet"
    có quan hệ "là học phần tiên quyết của" với X.

    TUYỆT ĐỐI KHÔNG:
    - Không đảo ngược câu kiểu: "Để học A cần học trước B" nếu A là tiên quyết của B.
    - Không tự diễn giải lại quan hệ.

    ---

    ### Trường hợp 3:
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A học phần X là tiên quyết của học phần nào?"

    QUY TẮC DIỄN GIẢI BẮT BUỘC:

    - Học phần X trong câu hỏi LUÔN LUÔN là "hoc_phan_tien_quyet".
    - Các học phần mà X là tiên quyết của LUÔN LUÔN nằm trong cột "hoc_phan_bi_tien_quyet".
    - Chỉ xét các bản ghi có:
    hoc_phan_tien_quyet == X
    - TUYỆT ĐỐI KHÔNG suy luận ngược chiều.

    CÁCH TRẢ LỜI:

    - Nếu KHÔNG tồn tại bản ghi nào có "hoc_phan_tien_quyet" == X:
    → Trả lời đúng 1 câu:
    "Không có học phần X trong chương trình đào tạo {ten_ctdt}."

    - Nếu CÓ:
    → Trả lời theo mẫu BẮT BUỘC:

    "Trong chương trình đào tạo {ten_ctdt}, học phần \"X\" là học phần tiên quyết của các học phần sau:"

    Sau đó liệt kê TẤT CẢ học phần trong cột "hoc_phan_bi_tien_quyet"
    tương ứng với học phần X.


    ---

    ### Trường hợp 4:
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A nếu rớt học phần X thì không được học học phần nào?"

    QUY TẮC DIỄN GIẢI BẮT BUỘC:

    - Học phần X trong câu hỏi LUÔN LUÔN là "hoc_phan_tien_quyet".
    - Các học phần KHÔNG ĐƯỢC HỌC nếu rớt X LUÔN LUÔN nằm trong cột "hoc_phan_bi_tien_quyet".
    - Chỉ xét các bản ghi có:
    hoc_phan_tien_quyet == X
    - TUYỆT ĐỐI KHÔNG diễn giải lại thành "để học X cần học trước môn nào".

    CÁCH TRẢ LỜI:

    - Nếu KHÔNG tồn tại bản ghi nào có "hoc_phan_tien_quyet" == X:
    → Trả lời đúng 1 câu:
    "Trong chương trình đào tạo {ten_ctdt}, học phần X không phải là học phần tiên quyết của học phần nào."

    - Nếu CÓ:
    → Trả lời theo mẫu BẮT BUỘC:

    "Trong chương trình đào tạo {ten_ctdt}, nếu bạn rớt học phần \"X\" thì bạn sẽ không được học các học phần sau:"

    Sau đó liệt kê TẤT CẢ học phần trong cột "hoc_phan_bi_tien_quyet"
    tương ứng với học phần X.

    TUYỆT ĐỐI KHÔNG:
    - Không dùng cấu trúc "Để học môn X, cần học trước..."
    - Không đảo chiều quan hệ.

    ---

    ### Trường hợp 5
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A học phần X có phải là học phần tiên quyết của học phần Y không?"

    → Thực hiện các bước:
    1. Kiểm tra X có tồn tại trong cột "hoc_phan_tien_quyet" không.
    Nếu không → trả lời không có học phần X trong chương trình đào tạo "{ten_ctdt}".
    2. Kiểm tra Y có tồn tại trong cột "hoc_phan_bi_tien_quyet" không.
    Nếu không → trả lời không có học phần Y trong chương trình đào tạo "{ten_ctdt}".
    3. Nếu cả hai đều tồn tại:
    - Nếu có quan hệ A là tiên quyết của B với A = X và B = Y
        → trả lời: học phần X là học phần tiên quyết của học phần Y.
    - Ngược lại → trả lời: học phần X không phải là học phần tiên quyết của học phần Y.

    ========================
    LƯU Ý DIỄN ĐẠT:
    ========================
    Các cách hỏi sau được xem là tương đương nhau:

    - "Công nghệ thông tin Nhật ..."
    - "Chương trình Công nghệ thông tin Nhật ..."
    - "Chương trình đào tạo Công nghệ thông tin Nhật ..."
    - "Trong chương trình đào tạo Công nghệ thông tin Nhật ..."

    Tất cả đều được hiểu là hỏi về cùng một chương trình đào tạo.

    Không được vì khác cách diễn đạt mà kết luận là không có dữ liệu.    
    =================================
    RÀNG BUỘC BẮT BUỘC
    =================================

    - Chỉ sử dụng dữ liệu đã cho.
    - Không suy đoán.
    - Không thêm học phần ngoài danh sách.
    - Không nhắc lại câu hỏi.
    - Không giải thích.
    - Không nhận xét.
    - Trả lời đúng trọng tâm câu hỏi.

    =================================
    ĐỊNH DẠNG TRẢ LỜI
    =================================

    - Văn bản ngắn gọn, rõ ràng.
    - Nếu liệt kê nhiều học phần → phân tách bằng dấu phẩy.
    """

        try:
            model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý tư vấn chương trình đào tạo đại học, trả lời chính xác dựa trên dữ liệu Neo4j."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ Lỗi GPT:", e)
            return "Xin lỗi, hệ thống gặp lỗi khi xử lý câu hỏi."


    def get_song_hanh(self, question: str, data: dict):

        danh_sach = data.get("song_hanh", [])
        ten_ctdt = data.get("ten_chuong_trinh", "")

        if not danh_sach:
            return f"Trong chương trình đào tạo {ten_ctdt}, không có học phần song hành."

        prompt = f"""
    Bạn là trợ lý học vụ đại học.

    Dữ liệu quan hệ học phần song hành của chương trình đào tạo "{ten_ctdt}":

    {danh_sach}

    =================================
    CÂU HỎI
    =================================
    "{question}"

    =================================
    QUY TẮC HIỂU DỮ LIỆU
    =================================

    Mỗi phần tử trong dữ liệu có dạng:

    - hoc_phan_1
    - hoc_phan_2
    - quan_he: "là học phần song hành với"

    → hiểu là:
    hoc_phan_1 và hoc_phan_2 có thể học song song trong cùng học kỳ.

    Mỗi học phần có thể kèm:
    - tien_quyet: danh sách học phần phải học trước

    =================================
    CÁC TRƯỜNG HỢP CẦN TRẢ LỜI
    =================================

    ### Trường hợp 1
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A có những quan hệ song hành nào?"
    - "Chương trình đào tạo A có những học phần song hành nào?"

    → PHẢI:
    - Duyệt TOÀN BỘ danh sách
    - Liệt kê TẤT CẢ các cặp học phần có quan hệ song hành
    - KHÔNG bỏ sót
    - KHÔNG chọn đại diện
    - KHÔNG gộp

    Trả lời theo mẫu:

    "Trong chương trình đào tạo {ten_ctdt}, các học phần có quan hệ song hành bao gồm:"
    Sau đó liệt kê từng cặp:
    "X" song hành với "Y"

    ---

    ### Trường hợp 2
    Câu hỏi dạng:
    - "Trong chương trình đào tạo A học phần X có mối quan hệ với học phần nào?"
    - "Học phần X có học song hành với học phần nào không?"

    QUY TẮC:
    - Kiểm tra học phần X có tồn tại trong:
    hoc_phan_1 HOẶC hoc_phan_2 hay không
    - Duyệt TOÀN BỘ danh sách

    CÁCH TRẢ LỜI:
    - Nếu KHÔNG tồn tại trong cả hai cột:
    → Trả lời đúng 1 câu:
    "Không có học phần X trong chương trình đào tạo {ten_ctdt}."

    - Nếu CÓ:
    → Trả lời theo mẫu:

    "Trong chương trình đào tạo {ten_ctdt}, học phần \"X\" có quan hệ song hành với các học phần sau:"

    Sau đó liệt kê TẤT CẢ học phần song hành với X
    (không phân biệt X nằm ở cột hoc_phan_1 hay hoc_phan_2)

    ---

    ### Trường hợp 3
    Câu hỏi dạng:
    - "Tôi có thể học X và Y cùng lúc trong chương trình A không?"
    - "Trong chương trình A học phần X và học phần Y có phải song hành không?"

    Kiểm tra xem thử học phần X có đứng chung 1 hàng với học phần Y trong tham số đầu vào mảng data không
        *   Nếu có trả lời: "Bạn có thể học học phần X và học phần Y cùng lúc trong chương trình đào tạo {ten_ctdt}.
        * Nếu không trả lời "Bạn không thể học học phần X và học phần Y cùng lúc trong chương trình đào tạo {ten_ctdt}.

    ========================
    LƯU Ý DIỄN ĐẠT:
    ========================
    Các cách hỏi sau được xem là tương đương nhau:

    - "Công nghệ thông tin Nhật ..."
    - "Chương trình Công nghệ thông tin Nhật ..."
    - "Chương trình đào tạo Công nghệ thông tin Nhật ..."
    - "Trong chương trình đào tạo Công nghệ thông tin Nhật ..."

    Tất cả đều được hiểu là hỏi về cùng một chương trình đào tạo.

    Không được vì khác cách diễn đạt mà kết luận là không có dữ liệ

    =================================
    RÀNG BUỘC BẮT BUỘC
    =================================

    - Chỉ sử dụng dữ liệu đã cho
    - Không suy đoán
    - Không thêm học phần ngoài danh sách
    - Không nhắc lại câu hỏi
    - Không giải thích thêm
    - Trả lời đúng trọng tâm

    =================================
    ĐỊNH DẠNG TRẢ LỜI
    =================================

    - Văn bản ngắn gọn
    - Nếu liệt kê nhiều học phần → phân tách bằng dấu phẩy
    """

        try:
            model_name = getattr(self, "model_reasoning", None) or "gpt-4o-mini"

            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý tư vấn chương trình đào tạo đại học, trả lời chính xác dựa trên dữ liệu Neo4j."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print("❌ Lỗi GPT:", e)
            return "Xin lỗi, hệ thống gặp lỗi khi xử lý câu hỏi."



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

# backend/intent_detector.py
from backend.config import client

# 🎯 Danh sách intent
 

INTENTS = {
    "hoi_dieu_kien_tot_nghiep_ctdt": "Hỏi về điều kiện tốt nghiệp hoặc chuẩn đầu ra của một chương trình đào tạo cụ thể.",
    "hoi_chuan_ngoai_ngu_dau_ra_chung": "Hỏi về chuẩn ngoại ngữ đầu ra chung của toàn trường (không nêu chương trình cụ thể).",
    "chuan_ngoai_ngu_ctdt": "Hỏi về chuẩn ngoại ngữ đầu ra của 1 CTĐT cụ thể (có tên CTĐT).", 
    "hoi_chuan_ngoai_ngu_muc_diem": "Hỏi về mức điểm ngoại ngữ (IELTS, TOEIC, JLPT...) để tốt nghiệp.", 
    "hoi_khung_nang_luc_ngoai_ngu": "Hỏi về khung năng lực ngoại ngữ 6 bậc Việt Nam (CEFR Việt Nam).", 
    "hoi_thong_tin_ctdt": "Hỏi về thông tin của một chương trình đào tạo (tên, khoa, tín chỉ, học phần, học kỳ...).", 
    "hoi_danh_sach_ctdt": "Hỏi danh sách tất cả các chương trình đào tạo.", 
    "hoi_tien_quyet_hoc_phan_ctdt": "Hỏi về quan hệ tiên quyết của một học phần trong một CTĐT.",
    "hoi_hoc_phan_song_hanh_ctdt": "Hỏi về quan hệ song hành của một học phần trong một CTĐT.",
    "hoi_dieu_kien_tot_nghiep_chung": "Khi có từ khóa điều kiện tốt nghiệp là gì"
}

class IntentDetector:
    def __init__(self):
        self.model = "gpt-4o-mini"

    # ========================
    # 1️⃣ Detect intent
    # ========================
    def detect_intent(self, question: str) -> str:

        q = question.lower()

        # ======================
        # RULE BASED ƯU TIÊN
        # ======================

        if any(k in q for k in [
            "khung năng lực",
            "khung 6 bậc",
            "ngoại ngữ gồm mấy bậc",
            "các bậc ngoại ngữ",
            "khung năng lực tiếng anh"
        ]):
            return "hoi_khung_nang_luc_ngoai_ngu"

        # Mức điểm chứng chỉ
        if any(k in q for k in ["bao nhiêu", "mức", "điểm"]) and any(
            k in q for k in ["ielts", "toeic", "toefl", "jlpt", "nat", "top j"]
        ):
            return "hoi_chuan_ngoai_ngu_muc_diem"

        # Điều kiện tốt nghiệp
        if "điều kiện tốt nghiệp" in q and "của" in q:
            return "hoi_dieu_kien_tot_nghiep_ctdt"

        if "điều kiện tốt nghiệp" in q:
            return "hoi_dieu_kien_tot_nghiep_chung"

        #  Chuẩn ngoại ngữ
        if "chuẩn ngoại ngữ" in q and "của" in q:
            return "chuan_ngoai_ngu_ctdt"

        if "chuẩn ngoại ngữ" in q:
            return "hoi_chuan_ngoai_ngu_dau_ra_chung"
        # ======================
        # GPT fallback
        # ======================

        prompt = f"""
    Phân loại intent câu hỏi học vụ vào 1 trong các intent sau:

    1 hoi_chuan_ngoai_ngu_dau_ra_chung → hỏi về chuẩn ngoại ngữ đầu ra của trường, ví dụ:
        - "Chuẩn ngoại ngữ đầu ra là gì?"
        - "Ra trường cần đạt chứng chỉ tiếng Anh nào?"
    2 chuan_ngoai_ngu_ctdt → hỏi về chuẩn ngoại ngữ đầu ra của một chương trình đào tạo cụ thể, ví dụ: 
        - "Chuẩn ngoại ngữ đầu ra của Công nghệ thông tin Nhật là gì?" 
    3 hoi_chuan_ngoai_ngu_muc_diem → Áp dụng cho các câu hỏi có từ khóa như: 
        - "IELTS bao nhiêu thì tốt nghiệp" 
        - "TOEIC bao nhiêu thì ra trường" 
        - "Cần đạt JLPT cấp mấy để tốt nghiệp" 
        - Có số điểm hoặc từ 'bao nhiêu', 'mức điểm', 'điểm bao nhiêu' 
    4 hoi_khung_nang_luc_ngoai_ngu → Các câu hỏi chứa các từ khóa như: 
        - "khung năng lực ngoại ngữ" 
        - "khung năng lực tiếng anh" 
        - "khung 6 bậc" 
        - "ngoại ngữ gồm mấy bậc" 
        - "các bậc ngoại ngữ" 
    5 hoi_thong_tin_ctdt
     Khi chọn **hoi_thong_tin_ctdt**: 
    - Câu hỏi chứa tên một *chương trình đào tạo* + có mục đích: 
        • hỏi thông tin CTĐT 
        • hỏi số tín chỉ 
        • hỏi CTĐT thuộc khoa nào 
        • hỏi danh sách học phần 
        • hỏi học phần theo học kỳ 
        • hỏi danh sách học phần đồ án
        • hỏi học phần theo loại: đại cương / tiên quyết / song hành / tự do / đồ án
        
    6 hoi_danh_sach_ctdt
    7 hoi_tien_quyet_hoc_phan_ctdt
    8 hoi_hoc_phan_song_hanh_ctdt

    Chỉ trả về đúng mã intent.

    Câu hỏi: "{question}"
    """

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            intent = response.choices[0].message.content.strip().lower()

            for key in INTENTS.keys():
                if key == intent:
                    return key

            return "hoi_thong_tin_ctdt"

        except Exception as e:
            print("❌ Lỗi khi xác định intent:", e)
            return "hoi_thong_tin_ctdt"

    def transform_question(self, question: str) -> str:
        q = question.lower().strip()

        replacements = {
            "chuẩn đầu ra": "điều kiện tốt nghiệp",
            "ra trường cần gì": "điều kiện tốt nghiệp",
            "yêu cầu tốt nghiệp": "điều kiện tốt nghiệp"
        }

        for old, new in replacements.items():
            q = q.replace(old, new)

        return q



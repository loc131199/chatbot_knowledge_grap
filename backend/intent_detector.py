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

        if "điều kiện tốt nghiệp" in q and "chuẩn" not in q:
            return "hoi_dieu_kien_tot_nghiep_chung"

        if "điều kiện tốt nghiệp" in q and "của" in q:
            return "hoi_dieu_kien_tot_nghiep_ctdt"

        if "chuẩn ngoại ngữ đầu ra" in q and "của" not in q:
            return "hoi_chuan_ngoai_ngu_dau_ra_chung"

        if "chuẩn ngoại ngữ đầu ra" in q and "của" in q:
            return "chuan_ngoai_ngu_ctdt"

        if any(x in q for x in ["ielts", "toeic", "toefl", "jlpt", "bao nhiêu", "mức điểm"]):
            return "hoi_chuan_ngoai_ngu_muc_diem"

        if any(x in q for x in ["khung", "6 bậc", "năng lực"]):
            return "hoi_khung_nang_luc_ngoai_ngu"

        # ======================
        # GPT fallback
        # ======================

        prompt = f"""
    Phân loại intent câu hỏi học vụ vào 1 trong các intent sau:

    hoi_dieu_kien_tot_nghiep_chung
    hoi_dieu_kien_tot_nghiep_ctdt
    hoi_chuan_ngoai_ngu_dau_ra_chung
    chuan_ngoai_ngu_ctdt
    hoi_chuan_ngoai_ngu_muc_diem
    hoi_khung_nang_luc_ngoai_ngu
    hoi_thong_tin_ctdt
    hoi_danh_sach_ctdt
    hoi_tien_quyet_hoc_phan_ctdt
    hoi_hoc_phan_song_hanh_ctdt

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

        # KHÔNG đổi câu hỏi chuẩn ngoại ngữ đầu ra
        if "chuẩn ngoại ngữ đầu ra" in q:
            return "chuẩn ngoại ngữ đầu ra là gì"

        return q


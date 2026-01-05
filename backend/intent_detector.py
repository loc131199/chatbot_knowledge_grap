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
    # 1️⃣ Xác định intent
    # ========================
    def detect_intent(self, question: str) -> str:
        
        prompt = f"""
Bạn là bộ phân loại intent cho chatbot học vụ Đại học Bách Khoa.

Phân loại câu hỏi vào **một trong các intent sau**:
1  hoi_dieu_kien_tot_nghiep_chung → Chỉ áp dụng khi có từ khóa là: "Điều kiện tốt nghiệp là gì".
    Lưu Ý: Nếu không có từ khóa "Điều kiện tốt nghiệp là gì" thì chắc chắn không phải là trường hợp này.

2  hoi_dieu_kien_tot_nghiep_ctdt → có tên chương trình ví dụ  như "Điều kiện tốt nghiệp của Công nghệ thông tin Nhật là gì".
3  hoi_chuan_ngoai_ngu_dau_ra_chung → hỏi về chuẩn ngoại ngữ đầu ra của trường, ví dụ:
    - "Chuẩn ngoại ngữ đầu ra là gì?"
    - "Ra trường cần đạt chứng chỉ tiếng Anh nào?"
4 chuan_ngoai_ngu_ctdt → hỏi về chuẩn ngoại ngữ đầu ra của một chương trình đào tạo cụ thể, ví dụ: 
    - "Chuẩn ngoại ngữ đầu ra của Công nghệ thông tin Nhật là gì?" 
5 hoi_chuan_ngoai_ngu_muc_diem → Áp dụng cho các câu hỏi có từ khóa như: 
    - "IELTS bao nhiêu thì tốt nghiệp" 
    - "TOEIC bao nhiêu thì ra trường" 
    - "Cần đạt JLPT cấp mấy để tốt nghiệp" 
    - Có số điểm hoặc từ 'bao nhiêu', 'mức điểm', 'điểm bao nhiêu' 
6 hoi_khung_nang_luc_ngoai_ngu → Các câu hỏi chứa các từ khóa như: 
    - "khung năng lực ngoại ngữ" 
    - "khung năng lực tiếng anh" 
    - "khung 6 bậc" 
    - "ngoại ngữ gồm mấy bậc" 
    - "các bậc ngoại ngữ" 
7 hoi_thong_tin_ctdt 
    Khi chọn **hoi_thong_tin_ctdt**: 
    - Câu hỏi chứa tên một *chương trình đào tạo* + có mục đích: 
        • hỏi thông tin CTĐT 
        • hỏi số tín chỉ 
        • hỏi CTĐT thuộc khoa nào 
        • hỏi danh sách học phần 
        • hỏi học phần theo học kỳ 
        • hỏi học phần theo loại: đại cương / tiên quyết / song hành / tự do / đồ án 
    Ví dụ: 
    - "Thông tin về chương trình Khoa học máy tính?" 
    - "CNTT Nhật học kỳ 1 gồm những môn gì?" 
    - "Những môn đại cương của Công nghệ phần mềm_PFIEV?" 
    - "Chương trình Kỹ thuật Năng lượng & Môi trường là chương trình đào tạo gì?" 
    - "Chương trình Kỹ thuật Tàu thủy thuộc khoa nào?" 
    - "CNTT đặc thù có bao nhiêu tín chỉ?" 
    - "Chương trình Kỹ thuật Hóa học gồm những học phần nào?" 
    - "Những học phần phải học trong học kỳ 3 của chương trình Công nghệ Thông tin Đặc thù là gì?" 

8 hoi_danh_sach_ctdt → Các câu hỏi dạng: 
    - “Danh sách các chương trình đào tạo?” 
    - “Có bao nhiêu chương trình đào tạo của trường đại học Bách Khoa?” 
    - “Liệt kê chương trình đào tạo của trường?” 
    - “Các ngành đào tạo của Bách Khoa?” 
    - “Trường có những ngành nào?” 
    - Những câu tương tự như trên 
    
9 hoi_tien_quyet_hoc_phan_ctdt → Các câu hỏi chứa các từ khóa như:
    -"học trước",
    -"không được học",
    -"nếu trượt",
    -"môn nào trước",
    -"phụ thuộc",
    -"phải hoàn thành trước",
    Ngoài ra các câu hỏi có dạng như:
    - Tiên quyết của học phần B trong chương trình đào tạo A?
    - Môn B là tiên quyết của những môn nào trong CTĐT A?
  Ví dụ:
        - "Trong chương trình A có những quan hệ tiên quyết nào?"
        - "Danh sách môn tiên quyết trong chương trình A này?"  
        - "nêú tôi trượt môn B thì tôi khổng thể học môn nào trong chương trình đào tạo A"
        - "Để học Vi xử lý chương trình A cần học trước môn nào?"
        - "Môn Cấu trúc dữ liệu chương trình A có tiên quyết gì không?"
        - "Trong chương trình A môn Lập trình C là tiên quyết cho những môn nào?"
        - "Những môn nào trong chương trình A yêu cầu Toán A1 làm tiên quyết?"

10  hoi_hoc_phan_song_hanh_ctdt → Các câu hỏi chứa các từ khóa như:       
    -"cùng lúc với",
    -"học cùng lúc",
    -"cùng lúc",
    
    Ngoài ra các câu hỏi có dạng như:
    - Hỏi song hành của một học phần X
    - Hỏi hai môn có thể học cùng lúc không?
  Ví dụ:
        - "trong chương trình công nghệ thông tin Nhật học phần nào là học phần tiên quyết"
        - "Trong CTĐT A môn X song hành với môn nào?"
        - "Học phần nào có mối quan hệ song hành với môn X trong CTĐT A"  
        - "Trong CTĐT A học phần nào có thể học cùng lúc với môn X"
        - "Tôi có thể học A và B cùng lúc trong chương trình C không?"
        - "Trong chương trình C A và B có phải song hành không?"
    
LƯU Ý: 
    - Nếu hỏi "chuẩn ngoại ngữ đầu ra là gì?" → KHÔNG phải mức điểm. 
    - Nếu hỏi "chuẩn ngoại ngữ đầu ra của CNTT Nhật?" → KHÔNG phải mức điểm. 
    - Chỉ chọn intent thứ 5 nếu câu hỏi liên quan trực tiếp đến mức điểm cụ thể. 
    - Câu hỏi về "khung năng lực ngoại ngữ" KHÔNG phải chuẩn đầu ra của CTĐT. 
    - Câu hỏi về "6 bậc, các bậc ngoại ngữ" cũng thuộc khung năng lực 
Câu hỏi: "{question}"

Trả về DUY NHẤT một trong 10 mã trên.
"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            intent = response.choices[0].message.content.strip().lower()
            for key in INTENTS.keys():
                if key in intent:
                    return key
            return "hoi_dieu_kien_tot_nghiep_chung"
        except Exception as e:
            print("❌ Lỗi khi xác định intent:", e)
            return "hoi_dieu_kien_tot_nghiep_chung"

    # ========================
    # 2️⃣ Biến đổi câu hỏi nếu cần
    # ========================
    def transform_question(self, question: str) -> str:
        """
        Biến đổi câu hỏi ở mức từ vựng — không thay đổi ý nghĩa.
        Dùng để chuẩn hóa từ ngữ trước khi BM25 search.
        """
        q = question.lower().strip()

        replacements = {
            "chuẩn đầu ra": "điều kiện tốt nghiệp",
            "ra trường cần gì": "điều kiện tốt nghiệp",
            "yêu cầu tốt nghiệp": "điều kiện tốt nghiệp"
        }

        for old, new in replacements.items():
            q = q.replace(old, new)

        # Giữ nguyên ngữ nghĩa của câu hỏi “chuẩn ngoại ngữ đầu ra là gì”
        # để IntentDetector có thể nhận diện riêng
        if "chuẩn ngoại ngữ đầu ra" in q:
            q = "chuẩn ngoại ngữ đầu ra là gì"

        return q
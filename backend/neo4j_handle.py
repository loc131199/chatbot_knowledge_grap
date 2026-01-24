# backend/neo4j_handler.py
from neo4j import GraphDatabase
from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, client
from backend.openai_handler import OpenAIHandler
import logging
import json
import re

logger = logging.getLogger(__name__)

     
class Neo4jHandler:
    def run_query(self, query, params=None):
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [r.data() for r in result]
            
    def __init__(self, openai_handler: OpenAIHandler = None):
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )

            with self.driver.session() as session:
                session.run("RETURN 1")

            self.openai_handler = openai_handler
            self.llm_client = openai_handler.client if openai_handler else None

            logger.info("✅ Kết nối Neo4j thành công!")

        except Exception as e:
            logger.error(f"❌ Lỗi khi kết nối Neo4j: {e}")
            raise e

    def close(self):
        if hasattr(self, "driver") and self.driver:
            self.driver.close()
            logger.info("🔒 Đã đóng kết nối Neo4j.")

    

    def extract_ctdt_name(self, question: str):
        """
        Trích xuất tên chương trình đào tạo từ câu hỏi bằng cách:
        - làm sạch câu hỏi
        - loại bỏ stopwords
        - chạy BM25 để match gần đúng tên CTĐT
        """

        stopwords = [
            "chương trình", "ctdt", "ctđt", "ngành",
            "là gì", "giới thiệu", "thuộc khoa nào",
            "học gì", "gồm những gì", "bao gồm",
            "nội dung", "cho mình hỏi", "tư vấn"
        ]

        clean = question.lower()
        for sw in stopwords:
            clean = clean.replace(sw, "")

        clean = clean.strip()

        # fallback — nếu rỗng thì dùng nguyên câu
        if not clean:
            clean = question

        # chạy BM25 để lấy tên CTĐT khớp nhất
        query = """
        CALL db.index.fulltext.queryNodes(
            'ChuongTrinhDaoTao_full_text',
            $q
        ) YIELD node, score
        RETURN node.ten_chuong_trinh AS ten, score
        ORDER BY score DESC
        LIMIT 1
        """

        with self.driver.session() as sess:
            result = sess.run(query, {"q": clean}).single()

        if result:
            return result["ten"]

        return None
    # # ==========================
    # # BM25 Fulltext Search
    # # ==========================
    
    def bm25_search(self, query, limit=5):
        """
        Tìm kiếm toàn văn bằng BM25 (Fulltext Search).
        """
        cypher = """
        CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $query)
        YIELD node, score
        RETURN node.ten_chuong_trinh AS ten_chuong_trinh,
               node.noi_dung AS noi_dung,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(cypher, {"query": query, "limit": limit})
            records = [r.data() for r in result]
        logger.info(f"🔍 BM25 Search trả về {len(records)} kết quả cho truy vấn: '{query}'")
        return records

    def extract_entities_from_question(self, question: str):

        program_name = None
        course_name = None
        semester_name = None

        try:
            # 1️⃣ Lấy danh sách entity từ Neo4j
            cypher = """
            MATCH (c:HocPhanTienQuyet) RETURN c.ten_mon AS name
            UNION
            MATCH (c:HocPhanDaiCuong) RETURN c.ten_mon AS name
            UNION
            MATCH (c:HocPhanKeTiep) RETURN c.ten_mon AS name
            UNION
            MATCH (c:HocPhanSongHanh) RETURN c.ten_mon AS name
            UNION
            MATCH (p:ChuongTrinhDaoTao) RETURN p.ten_chuong_trinh AS name
            UNION
            MATCH (s:HocKy) RETURN s.ten_hoc_ky AS name
            """

            result = self.run_query(cypher)
            entity_list = [r["name"] for r in result if r["name"]]

            print("🟢 Entity list from Neo4j:", entity_list[:20], "...")

            # 2️⃣ Kiểm tra LLM client
            if not self.llm_client:
                raise Exception("LLM client chưa được khởi tạo")

            # 3️⃣ Prompt cho LLM
            prompt = f"""
    Bạn là hệ thống trích xuất thực thể từ câu hỏi.

    Danh sách thực thể:
    {entity_list}

    Nhiệm vụ:
    Trích xuất 3 trường:

    - program_name: tên CHƯƠNG TRÌNH ĐÀO TẠO
    - course_name: tên HỌC PHẦN
    - semester_name: tên HỌC KỲ

    QUY TẮC:

    1. Nếu câu hỏi liên quan đến khoa, tín chỉ, chương trình, điều kiện tốt nghiệp → tên đó là program_name.
    2. Nếu tên đó là chương trình đào tạo → KHÔNG được gán vào course_name.
    3. course_name chỉ dùng cho học phần.
    4. semester_name chỉ dùng cho học kỳ.
    5. Không gán 1 tên cho 2 trường.

    Chỉ trả JSON, không markdown:

    {{
    "program_name": "... hoặc null",
    "course_name": "... hoặc null",
    "semester_name": "... hoặc null"
    }}

    Câu hỏi:
    "{question}"

    """

            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            raw = response.choices[0].message.content.strip()
            print("🔍 RAW LLM OUTPUT:", raw)

            # 4️⃣ Làm sạch markdown nếu có
            if raw.startswith("```"):
                raw = raw.replace("```json", "").replace("```", "").strip()

            data = json.loads(raw)

            program_name = data.get("program_name")
            course_name = data.get("course_name")
            semester_name = data.get("semester_name")

            print("🟡 Extracted:")
            print("   program_name:", program_name)
            print("   course_name:", course_name)
            print("   semester_name:", semester_name)

        except Exception as e:
            print("❌ Lỗi tách entity:", e)

        return program_name, course_name, semester_name



    # ==========================
    # Lấy điều kiện tốt nghiệp chung
    # ==========================
    def get_dieu_kien_tot_nghiep_chung(self):
        query = "*"  # tìm tất cả chương trình
        cypher = """
        CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $query)
        YIELD node AS ctdt, score

        OPTIONAL MATCH (dk:DieuKienTotNghiep)-[r:ĐOI_VOI]->(ctdt)

        OPTIONAL MATCH (ctdt)-[rel:CO_CHUAN_NGOAI_NGU_DAU_RA_LA|CO_CHUAN_NGOAI_NGU_DAU_RA_TOI_THIEU_LA]->(lang)
        WHERE lang IS NOT NULL

        WITH 
            ctdt, dk, r, score,
            collect({
                he: rel.he,
                lang_type: HEAD(labels(lang)),
                thong_tin_ngoai_ngu: CASE HEAD(labels(lang))
                    WHEN 'TiengAnh' THEN {
                        bac: lang.bac,
                        Cambridge: lang.Cambridge,
                        chung_chi: lang.chung_chi,
                        IELTS: lang.IELTS,
                        TOEFL_iBT: lang.TOEFL_iBT,
                        TOEFL_ITP: lang.TOEFL_ITP,
                        TOEIC: lang.TOEIC
                    }
                    WHEN 'TiengNhat' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        JLPT: lang.JLPT,
                        NAT_TEST: lang.NAT_TEST,
                        TOP_J: lang.TOP_J
                    }
                    WHEN 'TiengPhap' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        DELF_va_DALF: lang.DELF_va_DALF,
                        TCF: lang.TCF
                    }
                    ELSE NULL
                END
            }) AS ngoai_ngu_list

        RETURN 
            ctdt.ten_chuong_trinh AS ten_chuong_trinh,
            dk.quyet_dinh AS Quyet_dinh,
            dk.dieu_kien_chung AS dieu_kien_chung,
            coalesce(r.dieu_kien_rieng, "Không có yêu cầu riêng.") AS dieu_kien_rieng,
            [x IN ngoai_ngu_list WHERE x.lang_type IS NOT NULL] AS ngoai_ngu_list,
            score

        ORDER BY score DESC, ten_chuong_trinh
        """
        with self.driver.session() as session:
            result = session.run(cypher, {"query": query})
            data = [r.data() for r in result]

        logger.info(f"🎓 Lấy {len(data)} điều kiện tốt nghiệp (BM25).")
        return data

    # ==========================
    # Lấy điều kiện tốt nghiệp CTĐT cụ thể
    # ==========================
    def get_dieu_kien_tot_nghiep_ctdt(self, question: str):

        bm25_results = self.bm25_search(question, limit=1)
        if not bm25_results:
            logger.warning(f"⚠️ Không tìm thấy CTĐT cho truy vấn: {question}")
            return None

        ten_ctdt = bm25_results[0]["ten_chuong_trinh"]


        # 3️⃣ Truy vấn chi tiết node
        cypher = """
        CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $ten_ctdt)
        YIELD node AS ctdt, score
        WHERE toLower(ctdt.ten_chuong_trinh) CONTAINS toLower($ten_ctdt)

        OPTIONAL MATCH (dk:DieuKienTotNghiep)-[r:ĐOI_VOI]->(ctdt)

        OPTIONAL MATCH (ctdt)-[rel:CO_CHUAN_NGOAI_NGU_DAU_RA_LA]->(lang)

        WITH 
            ctdt, dk, r, score,
            collect({
                he: rel.he,
                lang_type: HEAD(labels(lang)),
                thong_tin_ngoai_ngu: CASE HEAD(labels(lang))
                    WHEN 'TiengAnh' THEN {
                        bac: lang.bac,
                        Cambridge: lang.Cambridge,
                        chung_chi: lang.chung_chi,
                        IELTS: lang.IELTS,
                        TOEFL_iBT: lang.TOEFL_iBT,
                        TOEFL_ITP: lang.TOEFL_ITP,
                        TOEIC: lang.TOEIC
                    }
                    WHEN 'TiengNhat' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        JLPT: lang.JLPT,
                        NAT_TEST: lang.NAT_TEST,
                        TOP_J: lang.TOP_J
                    }
                    WHEN 'TiengPhap' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        DELF_va_DALF: lang.DELF_va_DALF,
                        TCF: lang.TCF
                    }
                    ELSE null
                END
            }) AS ngoai_ngu_list

        RETURN 
            ctdt.ten_chuong_trinh AS ten_chuong_trinh,
            dk.quyet_dinh AS quyet_dinh,
            dk.dieu_kien_chung AS dieu_kien_chung,
            coalesce(r.dieu_kien_rieng, "Không có yêu cầu riêng.") AS dieu_kien_rieng,

            [x IN ngoai_ngu_list WHERE x.he = "Cử nhân"] AS chuan_ngoai_ngu_cu_nhan,

            [x IN ngoai_ngu_list WHERE x.he = "Kỹ sư"] AS chuan_ngoai_ngu_ky_su,

            score
        ORDER BY score DESC
        LIMIT 1;
        """
        with self.driver.session() as session:
                record = session.run(cypher, {"ten_ctdt": ten_ctdt}).single()

        if not record:
            logger.warning(f"⚠️ Không tìm thấy chi tiết CTĐT: {ten_ctdt}")
            return None

        data = {
            "ten_chuong_trinh": record["ten_chuong_trinh"],
            "quyet_dinh": record["quyet_dinh"],
            "dieu_kien_chung": record["dieu_kien_chung"],
            "dieu_kien_rieng": record["dieu_kien_rieng"],
            "chuan_ngoai_ngu_cu_nhan": record["chuan_ngoai_ngu_cu_nhan"],
            "chuan_ngoai_ngu_ky_su": record["chuan_ngoai_ngu_ky_su"]
        }

        logger.info(f"🎓 Lấy điều kiện tốt nghiệp cho CTĐT: {ten_ctdt}")
        return data

    # ==========================
    # Lấy chuẩn ngoại ngữ đầu ra nói chung
    # ==========================
    def get_chuan_ngoai_ngu_dau_ra_chung(self):
        query = """
        MATCH (ctdt:ChuongTrinhDaoTao)

        OPTIONAL MATCH (ctdt)-[rel:CO_CHUAN_NGOAI_NGU_DAU_RA_LA|CO_CHUAN_NGOAI_NGU_DAU_RA_TOI_THIEU_LA]->(lang)
        WHERE lang IS NOT NULL

        WITH 
            ctdt,
            collect({
                he: rel.he,
                lang_type: HEAD(labels(lang)),
                thong_tin_ngoai_ngu: CASE HEAD(labels(lang))
                    WHEN 'TiengAnh' THEN {
                        bac: lang.bac,
                        Cambridge: lang.Cambridge,
                        chung_chi: lang.chung_chi,
                        IELTS: lang.IELTS,
                        TOEFL_iBT: lang.TOEFL_iBT,
                        TOEFL_ITP: lang.TOEFL_ITP,
                        TOEIC: lang.TOEIC
                    }
                    WHEN 'TiengNhat' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        JLPT: lang.JLPT,
                        NAT_TEST: lang.NAT_TEST,
                        TOP_J: lang.TOP_J
                    }
                    WHEN 'TiengPhap' THEN {
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        DELF_va_DALF: lang.DELF_va_DALF,
                        TCF: lang.TCF
                    }
                    ELSE NULL
                END
            }) AS ngoai_ngu_list

        RETURN 
            ctdt.ten_chuong_trinh AS ten_chuong_trinh,

            [x IN ngoai_ngu_list 
                WHERE x.lang_type IS NOT NULL AND x.he = "Cử nhân"] 
                AS chuan_ngoai_ngu_cu_nhan,

            [x IN ngoai_ngu_list 
                WHERE x.lang_type IS NOT NULL AND x.he = "Kỹ sư"] 
                AS chuan_ngoai_ngu_ky_su

        ORDER BY ten_chuong_trinh;
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]
     # ==========================
    # Lấy chuẩn ngoại ngữ đầu ra của 1 chương trình đào tạo cụ thể
    # ==========================

    def get_chuan_ngoai_ngu_dau_ra_cua_ctdt(self, question: str):

        program_name, course_name, semester_name = self.extract_entities_from_question(question)
        if not program_name:
            logger.warning(" Không tách được program_name từ câu hỏi")
            return {
                "ten_chuong_trinh": None,
                "chuan_ngoai_ngu_cu_nhan": [],
                "chuan_ngoai_ngu_ky_su": [],
                "score": 0.0
            }

        # 2️⃣ Neo4j fulltext query dùng program_name

        cypher = f"""
        CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', '{program_name}')
        YIELD node AS ctdt, score
        WHERE toLower(ctdt.ten_chuong_trinh) CONTAINS toLower('{program_name}')

        OPTIONAL MATCH (ctdt)-[rel:CO_CHUAN_NGOAI_NGU_DAU_RA_LA|CO_CHUAN_NGOAI_NGU_DAU_RA_TOI_THIEU_LA]->(lang)

        WITH 
            ctdt, score,
            collect({{
                he: rel.he,
                lang_type: HEAD(labels(lang)),
                thong_tin_ngoai_ngu: CASE HEAD(labels(lang))
                    WHEN 'TiengAnh' THEN {{
                        bac: lang.bac,
                        Cambridge: lang.Cambridge,
                        chung_chi: lang.chung_chi,
                        IELTS: lang.IELTS,
                        TOEFL_iBT: lang.TOEFL_iBT,
                        TOEFL_ITP: lang.TOEFL_ITP,
                        TOEIC: lang.TOEIC
                    }}
                    WHEN 'TiengNhat' THEN {{
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        JLPT: lang.JLPT,
                        NAT_TEST: lang.NAT_TEST,
                        TOP_J: lang.TOP_J
                    }}
                    WHEN 'TiengPhap' THEN {{
                        bac: lang.bac,
                        chung_chi: lang.chung_chi,
                        DELF_va_DALF: lang.DELF_va_DALF,
                        TCF: lang.TCF
                    }}
                    ELSE NULL
                END
            }}) AS ngoai_ngu_list

        RETURN
            ctdt.ten_chuong_trinh AS ten_chuong_trinh,

            [x IN ngoai_ngu_list 
                WHERE x.he = "Cử nhân" AND x.lang_type IS NOT NULL] 
                AS chuan_ngoai_ngu_cu_nhan,

            [x IN ngoai_ngu_list 
                WHERE x.he = "Kỹ sư" AND x.lang_type IS NOT NULL] 
                AS chuan_ngoai_ngu_ky_su,

            score
        ORDER BY score DESC
        LIMIT 1
        """

        with self.driver.session() as session:
            record = session.run(cypher).single()


        if not record:
            return {
                "ten_chuong_trinh": program_name,
                "chuan_ngoai_ngu_cu_nhan": [],
                "chuan_ngoai_ngu_ky_su": [],
                "score": 0.0
            }

        data = {
            "ten_chuong_trinh": record["ten_chuong_trinh"],
            "chuan_ngoai_ngu_cu_nhan": record["chuan_ngoai_ngu_cu_nhan"],
            "chuan_ngoai_ngu_ky_su": record["chuan_ngoai_ngu_ky_su"],
            "score": float(record["score"]) if record["score"] else 0.0
        }

        print("🟢 FINAL DATA:", data)

        return data


     # ==========================
    # Lấy hỏi toiec bao nhiều thì tốt nghiệp (chung + chương trình đào tạo cụ thể)
    # ==========================

    def query_language_requirement(self, question: str):
        """
        Truy vấn chuẩn đầu ra ngoại ngữ theo câu hỏi người dùng.
        Pipeline:
        1️⃣ Thực hiện fulltext search BM25 trên Neo4j
        2️⃣ Thu thập dữ liệu ChuongTrinhDaoTao + NgoaiNgu
        3️⃣ Lọc theo chứng chỉ người dùng hỏi (TOEIC, IELTS, ...)
        """

        cert_keywords = [
            "TOEIC","IELTS","TOEFL_iBT","TOEFL_ITP","Cambridge","chung_chi",
            "JLPT","NAT_TEST","TOP_J","DELF_va_DALF","TCF"
        ]
        question_lower = question.lower()
        matched_cert = None
        for cert in cert_keywords:
            if cert.lower() in question_lower:
                matched_cert = cert
                break
        if not matched_cert:
            matched_cert = "TOEIC"  # default nếu không detect được

        cypher = """
        CALL db.index.fulltext.queryNodes('NgoaiNgu_fulltext', $query)
        YIELD node AS lang, score

        OPTIONAL MATCH (ctdt:ChuongTrinhDaoTao)
            -[rel:CO_CHUAN_NGOAI_NGU_DAU_RA_LA|CO_CHUAN_NGOAI_NGU_DAU_RA_TOI_THIEU_LA]->(lang)

        WITH lang, ctdt, rel, score,
            HEAD(labels(lang)) AS lang_type,
            ctdt.ten_chuong_trinh AS thuoc_chuong_trinh,
            rel.he AS he
        WHERE thuoc_chuong_trinh IS NOT NULL

        WITH thuoc_chuong_trinh, he, score, lang_type, COLLECT(lang) AS langs

        WITH thuoc_chuong_trinh, he, score, lang_type,
            CASE lang_type
                WHEN 'TiengAnh' THEN {
                    bac: [l IN langs | l.bac],
                    Cambridge: [l IN langs | l.Cambridge],
                    chung_chi: [l IN langs | l.chung_chi],
                    IELTS: [l IN langs | l.IELTS],
                    TOEFL_iBT: [l IN langs | l.TOEFL_iBT],
                    TOEFL_ITP: [l IN langs | l.TOEFL_ITP],
                    TOEIC: [l IN langs | l.TOEIC]
                }
                WHEN 'TiengNhat' THEN {
                    bac: [l IN langs | l.bac],
                    chung_chi: [l IN langs | l.chung_chi],
                    JLPT: [l IN langs | l.JLPT],
                    NAT_TEST: [l IN langs | l.NAT_TEST],
                    TOP_J: [l IN langs | l.TOP_J]
                }
                WHEN 'TiengPhap' THEN {
                    bac: [l IN langs | l.bac],
                    chung_chi: [l IN langs | l.chung_chi],
                    DELF_va_DALF: [l IN langs | l.DELF_va_DALF],
                    TCF: [l IN langs | l.TCF]
                }
                ELSE NULL
            END AS thong_tin

        RETURN 
            thuoc_chuong_trinh,
            he,
            score,
            lang_type,
            thong_tin
        ORDER BY score DESC;

        """

        with self.driver.session() as session:
            results = session.run(cypher, {"query": question})

            data = []
            for record in results:
                chuong_trinh = record["thuoc_chuong_trinh"]
                lang_type = record["lang_type"]
                thong_tin = record["thong_tin"]
                score = record["score"]

                if not thong_tin:
                    continue

                # Lọc chỉ giữ chứng chỉ matched_cert
                cert_data = thong_tin.get(matched_cert, [])
                if not cert_data:
                    continue

                # Loại trùng, bỏ None
                cert_data = list(set([v for v in cert_data if v is not None]))

                data.append({
                    "chuong_trinh": chuong_trinh,
                    "ngon_ngu": lang_type,
                    "cert": cert_data,
                    "score": score
                })

        logger.info(f"🎓 Lấy {len(data)} kết quả chuẩn ngoại ngữ cho chứng chỉ {matched_cert}.")
        return data, matched_cert
    # ==========================
    # hỏi Khung năng lực ngoại ngữ là gì và hung năng lưc ngoại ngữ gồm các bậc nào?
    # ==========================
    def get_khung_nang_luc_ngoai_ngu(self):
        cypher = """
        CALL db.index.fulltext.queryNodes("ft_khung_nang_luc", "khung năng lực ngoại ngữ")
        YIELD node AS khung, score
        OPTIONAL MATCH (khung)-[:BAO_GOM]->(lang)
        WITH khung, score, collect(lang) AS langs

        UNWIND langs AS l
        WITH khung, score, HEAD(labels(l)) AS lang_type, l
        WITH khung, score, lang_type, collect(l) AS group_langs

        WITH khung, score, collect(
        CASE lang_type
            WHEN 'TiengAnh' THEN {
            lang_type: lang_type,
            thong_tin: {
                bac: [x IN group_langs | x.bac],
                Cambridge: [x IN group_langs | x.Cambridge],
                chung_chi: [x IN group_langs | x.chung_chi],
                IELTS: [x IN group_langs | x.IELTS],
                TOEFL_iBT: [x IN group_langs | x.TOEFL_iBT],
                TOEFL_ITP: [x IN group_langs | x.TOEFL_ITP],
                TOEIC: [x IN group_langs | x.TOEIC]
            }
            }
            WHEN 'TiengNhat' THEN {
            lang_type: lang_type,
            thong_tin: {
                bac: [x IN group_langs | x.bac],
                chung_chi: [x IN group_langs | x.chung_chi],
                JLPT: [x IN group_langs | x.JLPT],
                NAT_TEST: [x IN group_langs | x.NAT_TEST],
                TOP_J: [x IN group_langs | x.TOP_J]
            }
            }
            WHEN 'TiengPhap' THEN {
            lang_type: lang_type,
            thong_tin: {
                bac: [x IN group_langs | x.bac],
                chung_chi: [x IN group_langs | x.chung_chi],
                DELF_va_DALF: [x IN group_langs | x.DELF_va_DALF],
                TCF: [x IN group_langs | x.TCF]
            }
            }
            WHEN 'TiengTrung' THEN {
            lang_type: lang_type,
            thong_tin: {
                bac: [x IN group_langs | x.bac],
                chung_chi: [x IN group_langs | x.chung_chi],
                HSK: [x IN group_langs | x.HSK],
                TOCFL: [x IN group_langs | x.TOCFL]
            }
            }
            ELSE {
            lang_type: lang_type,
            thong_tin: {
                bac: [x IN group_langs | x.bac],
                chung_chi: [x IN group_langs | x.chung_chi]
            }
            }
        END
        ) AS cac_ngon_ngu

        RETURN {
        khung: {khai_niem: khung.khai_niem},
        cac_ngon_ngu: [nn IN cac_ngon_ngu WHERE nn IS NOT NULL],
        score: score
        } AS info
        ORDER BY score DESC;
        """

        with self.driver.session() as session:
            raw_data = [r["info"] for r in session.run(cypher)]

        # --- Sắp xếp theo lang_type và bậc ---
        sorted_data = []
        lang_order = ["TiengAnh", "TiengPhap", "TiengNhat", "TiengTrung"]
        for lang_type in lang_order:
            for ng in raw_data[0]["cac_ngon_ngu"]:  # giả sử chỉ lấy khung đầu tiên
                if ng["lang_type"] == lang_type:
                    thong_tin = ng["thong_tin"]
                    bacs = thong_tin.get("bac", [])
                    bac_dict = {b: {} for b in bacs}
                    for key, values in thong_tin.items():
                        if key == "bac":
                            continue
                        for idx, val in enumerate(values):
                            if idx < len(bacs):
                                if key not in bac_dict[bacs[idx]]:
                                    bac_dict[bacs[idx]][key] = []
                                bac_dict[bacs[idx]][key].append(val)
                    sorted_data.append({
                        "lang_type": lang_type,
                        "bac_dict": bac_dict
                    })

        return {
            "khung": raw_data[0]["khung"],
            "cac_ngon_ngu": sorted_data,
            "score": raw_data[0]["score"]
        }

    # ==========================
    # hỏi Chương trình đào tạo là gì, đại cương, tự do phải học trong chương trình đào tạo?
    # chương trình đào tạo có những môn gì ? Số tín chỉ của chương trình đào tạo
    # ==========================
    def get_course(self, question: str):

        logger.debug(f"🔎 get_course question = {question}")

        program_name, course_name, semester_name = self.extract_entities_from_question(question)

        if not program_name:
            logger.warning("⚠️ Không trích xuất được tên chương trình đào tạo")
            return []

        cypher = """
        MATCH (hp)-[r:THUOC]->(ctdt:ChuongTrinhDaoTao {ten_chuong_trinh: $program_name})
        OPTIONAL MATCH (ctdt)-[:THUOC]->(k:Khoa)

        WITH
            ctdt,
            k,
            CASE
                WHEN r.he = 'Kỹ sư' THEN 'Kỹ sư'
                ELSE 'Cử nhân'
            END AS he,
            hp,
            r

        WITH
            ctdt,
            k,
            he,
            COLLECT({
                loai: labels(hp)[0],
                ten: hp.ten_mon,
                ma_hoc_phan: hp.ma_hoc_phan,
                he: r.he,
                so_tin_chi: hp.so_tin_chi
            }) AS danh_sach_hoc_phan

        RETURN
            ctdt.ten_chuong_trinh AS ten_chuong_trinh,

            k.ten_khoa AS ten_khoa,
            ctdt.khoa AS khoa,
            ctdt.noi_dung AS noi_dung,

            ctdt.tong_so_tin_chi_yeu_cau_doi_voi_ky_su AS tong_so_tin_chi_yeu_cau_doi_voi_ky_su,
            ctdt.so_tin_chi_bat_buoc_doi_voi_ky_su AS so_tin_chi_bat_buoc_doi_voi_ky_su,
            ctdt.so_tin_chi_tu_chon_doi_voi_ky_su AS so_tin_chi_tu_chon_doi_voi_ky_su,

            ctdt.tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan AS tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan,
            ctdt.so_tin_chi_bat_buoc_doi_voi_cu_nhan AS so_tin_chi_bat_buoc_doi_voi_cu_nhan,
            ctdt.so_tin_chi_tu_chon_doi_voi_cu_nhan AS so_tin_chi_tu_chon_doi_voi_cu_nhan,

            he,
            size(danh_sach_hoc_phan) AS tong_so_hoc_phan,
            danh_sach_hoc_phan

        ORDER BY he
        """

        with self.driver.session() as session:
            result = session.run(cypher, {
                "program_name": program_name
            })
            records = [r.data() for r in result]

        if not records:
            return []

        # =====================
        # Chuẩn hóa output cho OpenAI handler
        # =====================

        final_output = {
            "ten_chuong_trinh": records[0].get("ten_chuong_trinh"),
            "ten_khoa": records[0].get("ten_khoa"),
            "khoa": records[0].get("khoa"),
            "noi_dung": records[0].get("noi_dung"),

            "tong_so_tin_chi_yeu_cau_doi_voi_ky_su": records[0].get("tong_so_tin_chi_yeu_cau_doi_voi_ky_su"),
            "so_tin_chi_bat_buoc_doi_voi_ky_su": records[0].get("so_tin_chi_bat_buoc_doi_voi_ky_su"),
            "so_tin_chi_tu_chon_doi_voi_ky_su": records[0].get("so_tin_chi_tu_chon_doi_voi_ky_su"),

            "tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan": records[0].get("tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan"),
            "so_tin_chi_bat_buoc_doi_voi_cu_nhan": records[0].get("so_tin_chi_bat_buoc_doi_voi_cu_nhan"),
            "so_tin_chi_tu_chon_doi_voi_cu_nhan": records[0].get("so_tin_chi_tu_chon_doi_voi_cu_nhan"),

            "hoc_phan_theo_he": []
        }

        for r in records:
            final_output["hoc_phan_theo_he"].append({
                "he": r.get("he"),
                "tong_so_hoc_phan": r.get("tong_so_hoc_phan"),
                "danh_sach_hoc_phan": r.get("danh_sach_hoc_phan")
            })

        return final_output


    # Hỏi về nhưng học phần học trong học kỳ bất kỳ 
    def get_hoc_phan_theo_hoc_ky_ctdt(self, question: str):
        logger.debug(f"🔎 get_hoc_phan_theo_hoc_ky_ctdt question = {question}")

        program_name, course_name, semester_name = self.extract_entities_from_question(question)

        if not program_name:
            logger.warning("⚠️ Thiếu tên chương trình đào tạo")
            return []

        cypher = """
        MATCH (c:ChuongTrinhDaoTao {ten_chuong_trinh: $program_name})
        <-[:THUOC]-(hp)
        -[:SE_HOC_TRONG]->(hk:HocKy)
        WHERE
            hp:HocPhanDaiCuong
        OR hp:HocPhanTienQuyet
        OR hp:HocPhanSongHanh
        OR hp:HocPhanKeTiep
        OR hp:HocPhanTuDo
        RETURN DISTINCT
            hp.ten_mon AS ten_mon,
            hp.ma_hoc_phan AS ma_hoc_phan,
            hp.so_tin_chi AS so_tin_chi,
            hk.ten_hoc_ky AS ten_hoc_ky,
            c.ten_chuong_trinh AS ten_chuong_trinh
        ORDER BY hk.ten_hoc_ky, hp.ten_mon
        """

        with self.driver.session() as session:
            result = session.run(cypher, {
                "program_name": program_name
            })
            records = [r.data() for r in result]
        
        print("🟢 Neo4j RAW RESULT:")
        for r in records:
            print(r)

        if not records:
            return []

        # =====================
        # Chuẩn hóa output
        # =====================

        final_output = {
            "ten_chuong_trinh": program_name,
            "danh_sach_hoc_phan": []
        }

        for r in records:
            final_output["danh_sach_hoc_phan"].append({
                "ten_mon": r.get("ten_mon"),
                "ma_hoc_phan": r.get("ma_hoc_phan"),
                "so_tin_chi": r.get("so_tin_chi"),
                "ten_hoc_ky": r.get("ten_hoc_ky")
            })

        return final_output


    # ==========================
    # Hỏi về danh sách chương trình đào tạo
    # ==========================
    def get_list_course(self):
        """
        Lấy danh sách tất cả chương trình đào tạo.
        Trả về mỗi CTĐT gồm:
        - ten_chuong_trinh
        - ma_chuong_trinh
        - tong_so_tin_chi_yeu_cau
        """

        cypher = """
            MATCH (ct:ChuongTrinhDaoTao)
            RETURN 
                ct.ten_chuong_trinh AS ten_chuong_trinh,
                ct.khoa AS Khoa,
                ct.ma_chuong_trinh AS ma_chuong_trinh,
                ct.tong_so_tin_chi_yeu_cau_doi_voi_ky_su AS tong_so_tin_chi_yeu_cau_doi_voi_ky_su,
                ct.so_tin_chi_bat_buoc_doi_voi_ky_su AS so_tin_chi_bat_buoc_doi_voi_ky_su,
                ct.so_tin_chi_tu_chon_doi_voi_ky_su AS so_tin_chi_tu_chon_doi_voi_ky_su,
                ct.tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan AS tong_so_tin_chi_yeu_cau_doi_voi_cu_nhan,
                ct.so_tin_chi_bat_buoc_doi_voi_cu_nhan AS so_tin_chi_bat_buoc_doi_voi_cu_nhan,
                ct.so_tin_chi_tu_chon_doi_voi_cu_nhan AS so_tin_chi_tu_chon_doi_voi_cu_nhan
        """

        with self.driver.session() as session:
            result = session.run(cypher)
            data_raw = [r.data() for r in result]

        return data_raw
    # ==========================
    # Hỏi về học phần tiên quyết của chương trình đào tạo
    # ==========================
    def get_tien_quyet(self, question: str):

        logger.debug(f"🔎 get_tien_quyet question = {question}")

        program_name, course_name, semester_name = self.extract_entities_from_question(question)

        if not program_name:
            logger.warning("⚠️ Thiếu tên chương trình đào tạo")
            return []

        cypher = """
        MATCH (c:ChuongTrinhDaoTao {ten_chuong_trinh: $program_name})
        <-[:THUOC]-(tq)
        -[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp)-[:THUOC]->(c)
        WHERE
            tq:HocPhanDaiCuong
            OR tq:HocPhanTienQuyet
            OR tq:HocPhanSongHanh
            OR tq:HocPhanKeTiep
            OR tq:HocPhanTuDo
        RETURN DISTINCT
            c.ten_chuong_trinh AS ten_chuong_trinh,
            tq.ten_mon AS ten_hoc_phan_tien_quyet,
            labels(tq) AS labels_tq,
            tq.ma_hoc_phan AS ma_hoc_phan_tien_quyet,
            tq.so_tin_chi AS so_tin_chi_tien_quyet,
            hp.ten_mon AS ten_hoc_phan_bi_tien_quyet,
            hp.ma_hoc_phan AS ma_hoc_phan_bi_tien_quyet,
            labels(hp) AS labels_hp
        ORDER BY tq.ten_mon, hp.ten_mon
        """

        with self.driver.session() as session:
            result = session.run(cypher, {
                "program_name": program_name
            })
            records = [r.data() for r in result]

        print("🟢 Neo4j RAW RESULT:")
        for r in records:
            print(r)

        if not records:
            return []

        # =====================
        # Chuẩn hóa output
        # =====================

        final_output = {
            "ten_chuong_trinh": program_name,
            "danh_sach_tien_quyet": []
        }

        seen = set()

        for r in records:
            key = (
                r.get("ten_hoc_phan_tien_quyet"),
                r.get("ten_hoc_phan_bi_tien_quyet")
            )

            if key in seen:
                continue
            seen.add(key)

            final_output["danh_sach_tien_quyet"].append({
                "hoc_phan_tien_quyet": r.get("ten_hoc_phan_tien_quyet"),
                "ma_hoc_phan_tien_quyet": r.get("ma_hoc_phan_tien_quyet"),
                "loai_hoc_phan_cua_hoc_phan_tien_quyet":  r.get("labels_tq"),
                "so_tin_chi_tien_quyet": r.get("so_tin_chi_tien_quyet"),
                "hoc_phan_bi_tien_quyet": r.get("ten_hoc_phan_bi_tien_quyet"),
                "ma_hoc_phan_bi_tien_quyet": r.get("ma_hoc_phan_bi_tien_quyet"),
                "loai_hoc_phan_cua_hoc_phan_bi_tien_quyet":  r.get("labels_hp"),
                "quan_he": "là học phần tiên quyết của"
            })

        return final_output

     # ==========================
    # Hỏi về học phần song hành của chương trình đào tạo
    # ==========================
    def get_song_hanh(self, question: str):

        logger.debug(f"🔎 get_song_hanh(): question='{question}'")

        program_name, course_name, semester_name = self.extract_entities_from_question(question)

        if not program_name:
            return "Bạn chưa cung cấp tên chương trình đào tạo."

        cypher = """
        MATCH (c:ChuongTrinhDaoTao {ten_chuong_trinh: $program_name})
            <-[:THUOC]-(hp1)-[:LA_HOC_PHAN_SONG_HANH_VOI]->(hp2)-[:THUOC]->(c)

        OPTIONAL MATCH (c)<-[:THUOC]-(tq1)-[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp1)
        OPTIONAL MATCH (c)<-[:THUOC]-(tq2)-[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp2)

        RETURN
            c.ten_chuong_trinh AS ten_chuong_trinh,
            hp1.ten_mon AS hoc_phan_1,
            labels(hp1) AS labels_hp1,
            hp1.ma_hoc_phan AS ma_hoc_hoc_phan_1,
            hp1.so_tin_chi AS so_tin_chi_hoc_phan_1,
            hp2.ten_mon AS hoc_phan_2,
            labels(hp2) AS labels_hp2,
            hp2.ma_hoc_phan AS ma_hoc_hoc_phan_2,
            hp2.so_tin_chi AS so_tin_chi_hoc_phan_2,
            collect(DISTINCT tq1.ten_mon) AS tien_quyet_hp1,
            collect(DISTINCT tq2.ten_mon) AS tien_quyet_hp2
        ORDER BY hoc_phan_1, hoc_phan_2
        """

        with self.driver.session() as session:
            result = session.run(cypher, {"program_name": program_name})
            rows = [r.data() for r in result]

        if not rows:
            return f"Trong chương trình đào tạo {program_name}, không có học phần song hành."

        song_hanh_list = []
        seen = set()

        for r in rows:
            hp1 = (r.get("hoc_phan_1") or "").strip()
            hp2 = (r.get("hoc_phan_2") or "").strip()

            if not hp1 or not hp2:
                continue

            key = tuple(sorted([hp1, hp2]))
            if key in seen:
                continue
            seen.add(key)

            song_hanh_list.append({
                "hoc_phan_1": {
                    "ten": hp1,
                    "ma_hoc_phan": r.get("ma_hoc_hoc_phan_1"),
                    "so_tin_chi": r.get("so_tin_chi_hoc_phan_1"),
                    "labels": r.get("labels_hp1"),
                    "tien_quyet": [x for x in r.get("tien_quyet_hp1", []) if x]
                },
                "quan_he": "là học phần song hành với",
                "hoc_phan_2": {
                    "ten": hp2,
                    "ma_hoc_phan": r.get("ma_hoc_hoc_phan_2"),
                    "so_tin_chi": r.get("so_tin_chi_hoc_phan_2"),
                    "labels": r.get("labels_hp2"),
                    "tien_quyet": [x for x in r.get("tien_quyet_hp2", []) if x]
                }
            })


        final_output = {
            "ten_chuong_trinh": program_name,
            "song_hanh": song_hanh_list
        }

        return final_output



         


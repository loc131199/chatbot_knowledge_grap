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

    

    # def extract_ctdt_name(self, question: str):
    #     """
    #     Trích xuất tên chương trình đào tạo từ câu hỏi bằng cách:
    #     - làm sạch câu hỏi
    #     - loại bỏ stopwords
    #     - chạy BM25 để match gần đúng tên CTĐT
    #     """

    #     stopwords = [
    #         "chương trình", "ctdt", "ctđt", "ngành",
    #         "là gì", "giới thiệu", "thuộc khoa nào",
    #         "học gì", "gồm những gì", "bao gồm",
    #         "nội dung", "cho mình hỏi", "tư vấn"
    #     ]

    #     clean = question.lower()
    #     for sw in stopwords:
    #         clean = clean.replace(sw, "")

    #     clean = clean.strip()

    #     # fallback — nếu rỗng thì dùng nguyên câu
    #     if not clean:
    #         clean = question

    #     # chạy BM25 để lấy tên CTĐT khớp nhất
    #     query = """
    #     CALL db.index.fulltext.queryNodes(
    #         'ChuongTrinhDaoTao_full_text',
    #         $q
    #     ) YIELD node, score
    #     RETURN node.ten_chuong_trinh AS ten, score
    #     ORDER BY score DESC
    #     LIMIT 1
    #     """

    #     with self.driver.session() as sess:
    #         result = sess.run(query, {"q": clean}).single()

    #     if result:
    #         return result["ten"]

    #     return None
    # # ==========================
    # # BM25 Fulltext Search
    # # ==========================
    
    # def bm25_search(self, query, limit=5):
    #     """
    #     Tìm kiếm toàn văn bằng BM25 (Fulltext Search).
    #     """
    #     cypher = """
    #     CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $query)
    #     YIELD node, score
    #     RETURN node.ten_chuong_trinh AS ten_chuong_trinh,
    #            node.noi_dung AS noi_dung,
    #            score
    #     ORDER BY score DESC
    #     LIMIT $limit
    #     """
    #     with self.driver.session() as session:
    #         result = session.run(cypher, {"query": query, "limit": limit})
    #         records = [r.data() for r in result]
    #     logger.info(f"🔍 BM25 Search trả về {len(records)} kết quả cho truy vấn: '{query}'")
    #    return records
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
    Bạn là hệ thống trích xuất thực thể.

    Danh sách thực thể:
    {entity_list}

    Câu hỏi:
    "{question}"

    Trả về JSON đúng định dạng, KHÔNG markdown:

    {{
    "program_name": "... hoặc null",
    "course_name": "... hoặc null",
    "semester_name": "... hoặc null"
    }}
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
    # hỏi Chương trình đào tạo là gì,  những học phần tiên quyết, đại cương, song hành, tự do phải học trong chương trình đào tạo?
    # , những môn phải học trong học kỳ của chương trình đào tạo . Học những môn gì trong chương trình đào tạo ?
    # ==========================
    def get_course(self, question: str):
        """
        Truy vấn CTĐT + các loại học phần (ĐC, SH, TD, KT, TQ, Đồ án) + gom học kỳ + thống kê.
        - Nhận diện Đồ án chỉ bằng PBL (không phân biệt hoa/thường).
        - Gộp nhiều "loại" của cùng một học phần thành 1 bản ghi (loai là list).
        """
        logger.debug(f"🔎 Querying with question='{question}'")

        extracted_name = self.extract_ctdt_name(question)
        if extracted_name:
            question = extracted_name

        cypher = """
            CALL db.index.fulltext.queryNodes(
                'ChuongTrinhDaoTao_full_text',
                $question
            )
            YIELD node AS ctdt, score

            WHERE toLower(ctdt.ten_chuong_trinh) CONTAINS toLower($question)

            OPTIONAL MATCH (ctdt)-[:THUOC]->(k:Khoa)

            /////////////////////////
            // Đại cương
            /////////////////////////
            OPTIONAL MATCH (hpdc:HocPhanDaiCuong)-[:THUOC]->(ctdt)
            OPTIONAL MATCH (hpdc)-[:SE_HOC_TRONG]->(hky_dc:HocKy)
            WITH ctdt, k, score,
                collect(DISTINCT{
                    loai: 'HocPhanDaiCuong',
                    ten: hpdc.ten_mon,
                    so_tin_chi: hpdc.so_tin_chi,
                    hoc_ky: hky_dc.ten_hoc_ky
                }) AS ds_dc

            /////////////////////////
            // Song hành
            /////////////////////////
            OPTIONAL MATCH (hpsh:HocPhanSongHanh)-[:THUOC]->(ctdt)
            OPTIONAL MATCH (hpsh)-[:SE_HOC_TRONG]->(hky_sh:HocKy)
            WITH ctdt, k, score, ds_dc,
                collect(DISTINCT{
                    loai: 'HocPhanSongHanh',
                    ten: hpsh.ten_mon,
                    so_tin_chi: hpsh.so_tin_chi,
                    hoc_ky: hky_sh.ten_hoc_ky
                }) AS ds_sh

            /////////////////////////
            // Tự do
            /////////////////////////
            OPTIONAL MATCH (hptd:HocPhanTuDo)-[:THUOC]->(ctdt)
            OPTIONAL MATCH (hptd)-[:SE_HOC_TRONG]->(hky_td:HocKy)
            WITH ctdt, k, score, ds_dc, ds_sh,
                collect(DISTINCT{
                    loai: 'HocPhanTuDo',
                    ten: hptd.ten_mon,
                    so_tin_chi: hptd.so_tin_chi,
                    hoc_ky: hky_td.ten_hoc_ky
                }) AS ds_td

            /////////////////////////
            // Kế tiếp
            /////////////////////////
            OPTIONAL MATCH (hpkt:HocPhanKeTiep)-[:THUOC]->(ctdt)
            OPTIONAL MATCH (hpkt)-[:SE_HOC_TRONG]->(hky_kt:HocKy)
            WITH ctdt, k, score, ds_dc, ds_sh, ds_td,
                collect(DISTINCT{
                    loai: 'HocPhanKeTiep',
                    ten: hpkt.ten_mon,
                    so_tin_chi: hpkt.so_tin_chi,
                    hoc_ky: hky_kt.ten_hoc_ky
                }) AS ds_kt

            /////////////////////////
            // Tiên quyết
            /////////////////////////
            OPTIONAL MATCH (hptq:HocPhanTienQuyet)-[:THUOC]->(ctdt)
            OPTIONAL MATCH (hptq)-[:SE_HOC_TRONG]->(hky_tq:HocKy)
            WITH ctdt, k, score, ds_dc, ds_sh, ds_td, ds_kt,
                collect(DISTINCT{
                    loai: 'HocPhanTienQuyet',
                    ten: hptq.ten_mon,
                    so_tin_chi: hptq.so_tin_chi,
                    hoc_ky: hky_tq.ten_hoc_ky
                }) AS ds_tq

            /////////////////////////
            // Học phần Đồ án (chỉ PBL)
            /////////////////////////
            OPTIONAL MATCH (hpdo)-[:THUOC]->(ctdt)
            WHERE hpdo.ten_mon IS NOT NULL AND toUpper(hpdo.ten_mon) CONTAINS 'PBL'
            OPTIONAL MATCH (hpdo)-[:SE_HOC_TRONG]->(hky_do:HocKy)
            WITH ctdt, k, score, ds_dc, ds_sh, ds_td, ds_kt, ds_tq,
                collect(DISTINCT{
                    loai: 'HocPhanDoAn',
                    ten: hpdo.ten_mon,
                    so_tin_chi: hpdo.so_tin_chi,
                    hoc_ky: hky_do.ten_hoc_ky
                }) AS ds_da

            /////////////////////////
            // Trả về
            /////////////////////////
            RETURN
                ctdt.ten_chuong_trinh AS ten_chuong_trinh,
                coalesce(ctdt.ma_chuong_trinh, '') AS ma_chuong_trinh,
                ctdt.noi_dung AS noi_dung,
                ctdt.tong_so_tin_chi_yeu_cau AS so_tin_chi,
                k.ten_khoa AS ten_khoa,

                ds_dc AS hoc_phan_dai_cuong,
                ds_sh AS hoc_phan_song_hanh,
                ds_td AS hoc_phan_tu_do,
                ds_kt AS hoc_phan_ke_tiep,
                ds_tq AS hoc_phan_tien_quyet,
                ds_da AS hoc_phan_do_an,

                size(ds_dc) AS tong_dc,
                size(ds_sh) AS tong_sh,
                size(ds_td) AS tong_td,
                size(ds_kt) AS tong_kt,
                size(ds_tq) AS tong_tq,
                size(ds_da) AS tong_da,

                score
            ORDER BY score DESC, ten_chuong_trinh
            LIMIT 1
        """

        with self.driver.session() as session:
            result = session.run(cypher, {"question": question})
            data_raw = [r.data() for r in result]

        if not data_raw:
            return []

        rec = data_raw[0]

        # đảm bảo các list tồn tại (tránh KeyError nếu DB trả None)
        ds_dc = rec.get("hoc_phan_dai_cuong") or []
        ds_sh = rec.get("hoc_phan_song_hanh") or []
        ds_td = rec.get("hoc_phan_tu_do") or []
        ds_kt = rec.get("hoc_phan_ke_tiep") or []
        ds_tq = rec.get("hoc_phan_tien_quyet") or []
        ds_da = rec.get("hoc_phan_do_an") or []

        # GỘP CÁC BẢN GHI THEO TÊN HỌC PHẦN (để tránh in trùng khi 1 HP có nhiều loại)
        # key: (ten, hoc_ky) -> value: {ten, so_tin_chi, hoc_ky, loai:set()}
        ds_grouped = {}

        def add_to_group(hp):
            ten = hp.get("ten") or "Không rõ tên"
            hk = hp.get("hoc_ky") or "Không rõ học kỳ"
            stc = hp.get("so_tin_chi")
            key = (ten.strip(), hk)
            if key not in ds_grouped:
                ds_grouped[key] = {
                    "ten": ten.strip(),
                    "so_tin_chi": stc,
                    "hoc_ky": hk,
                    "loai": set()
                }
            # thêm loại
            loai = hp.get("loai")
            if loai:
                ds_grouped[key]["loai"].add(loai)
            # nếu chưa có so_tin_chi nhưng bản ghi sau có, cập nhật
            if ds_grouped[key].get("so_tin_chi") is None and stc is not None:
                ds_grouped[key]["so_tin_chi"] = stc

        for hp in (ds_dc + ds_sh + ds_td + ds_kt + ds_tq + ds_da):
            add_to_group(hp)

        # Chuyển ds_grouped thành list và chuẩn hóa 'loai' từ set -> danh sách theo thứ tự mong muốn
        # Thứ tự hiển thị loại (ưu tiên đồ án trước)
        LOAI_ORDER = [
            "HocPhanDoAn",
            "HocPhanDaiCuong",
            "HocPhanTienQuyet",
            "HocPhanSongHanh",
            "HocPhanKeTiep",
            "HocPhanTuDo"
        ]

        # mapping hiển thị tiếng Việt
        LOAI_LABEL = {
            "HocPhanDoAn": "Học Phần Đồ Án",
            "HocPhanDaiCuong": "Học Phần Đại Cương",
            "HocPhanTienQuyet": "Học Phần Tiên Quyết",
            "HocPhanSongHanh": "Học Phần Song Hành",
            "HocPhanKeTiep": "Học Phần Kế Tiếp",
            "HocPhanTuDo": "Học Phần Tự Do"
        }

        ds_grouped_list = []
        for (ten, hk), v in ds_grouped.items():
            loai_list = [l for l in LOAI_ORDER if l in v["loai"]]
            # map sang label hiển thị
            loai_label_list = [LOAI_LABEL.get(l, l) for l in loai_list]
            ds_grouped_list.append({
                "ten": v["ten"],
                "so_tin_chi": v.get("so_tin_chi"),
                "hoc_ky": v["hoc_ky"],
                "loai": loai_list,            # giữ dạng code cho thống kê nếu cần
                "loai_label": loai_label_list # để hiển thị dễ đọc
            })

        # Sắp xếp theo học kỳ (dùng regex lấy số) rồi theo tên
        def hk_key(h):
            m = re.search(r"(\d+)", str(h))
            return int(m.group(1)) if m else 9999

        ds_grouped_list.sort(key=lambda x: (hk_key(x["hoc_ky"]), x["ten"]))

        # Tạo hoc_ky_map: { "Học kỳ 1": [ {ten, loai_label_str, so_tin_chi}, ... ], ... }
        hoc_ky_map = {}
        thong_ke_hk = {}

        # khởi tạo counters tổng theo loại
        totals = {"dc": 0, "sh": 0, "td": 0, "kt": 0, "tq": 0, "da": 0}

        for item in ds_grouped_list:
            hk = item.get("hoc_ky") or "Không rõ học kỳ"
            if hk not in hoc_ky_map:
                hoc_ky_map[hk] = []
                thong_ke_hk[hk] = {"dc": 0, "sh": 0, "td": 0, "kt": 0, "tq": 0, "da": 0}

            # hiển thị loai nối bằng " - " sử dụng label
            loai_label_str = " - ".join(item.get("loai_label", [])) if item.get("loai_label") else "Không rõ loại"

            hoc_ky_map[hk].append({
                "ten": item["ten"],
                "loai": loai_label_str,
                "so_tin_chi": item.get("so_tin_chi")
            })

            # tăng counters: nếu 1 học phần có nhiều loại, tăng từng loại
            for l in item.get("loai", []):
                key = {
                    "HocPhanDaiCuong": "dc",
                    "HocPhanSongHanh": "sh",
                    "HocPhanTuDo": "td",
                    "HocPhanKeTiep": "kt",
                    "HocPhanTienQuyet": "tq",
                    "HocPhanDoAn": "da"
                }.get(l)
                if key:
                    thong_ke_hk[hk][key] += 1
                    totals[key] += 1

        # sort hoc ky keys
        hoc_ky_sorted = {hk: hoc_ky_map[hk] for hk in sorted(hoc_ky_map, key=hk_key)}
        thong_ke_sorted = {hk: thong_ke_hk[hk] for hk in sorted(thong_ke_hk, key=hk_key)}

        final_output = {
            "ten_chuong_trinh": rec.get("ten_chuong_trinh"),
            "ma_chuong_trinh": rec.get("ma_chuong_trinh"),
            "ten_khoa": rec.get("ten_khoa"),
            "so_tin_chi": rec.get("so_tin_chi"),
            "noi_dung": rec.get("noi_dung"),

            "hoc_ky": hoc_ky_sorted,
            "thong_ke": {
                "tong_dc": totals["dc"],
                "tong_sh": totals["sh"],
                "tong_td": totals["td"],
                "tong_kt": totals["kt"],
                "tong_tq": totals["tq"],
                "tong_da": totals["da"],
                "theo_hoc_ky": thong_ke_sorted
            },

            "score": rec.get("score")
        }

        return [final_output]
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
                ct.ma_chuong_trinh AS ma_chuong_trinh,
                ct.tong_so_tin_chi_yeu_cau AS tong_so_tin_chi
        """

        with self.driver.session() as session:
            result = session.run(cypher)
            data_raw = [r.data() for r in result]

        return data_raw
    # ==========================
    # Hỏi về học phần tiên quyết của chương trình đào tạo
    # ==========================
   
    def get_tien_quyet(self, question: str):

        logger.debug(f"🔎 get_tien_quyet(): question='{question}'")

        # Trích tên CTĐT nếu có (giống get_course)
        extracted_name = self.extract_ctdt_name(question)
        if extracted_name:
            question = extracted_name

        cypher = """
            CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $question)
            YIELD node AS ctdt, score
            WHERE toLower(ctdt.ten_chuong_trinh) CONTAINS toLower($question)

            MATCH (hp1)-[:THUOC]->(ctdt)
            MATCH (hp1)-[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp2)
            MATCH (hp2)-[:THUOC]->(ctdt)

            RETURN DISTINCT
                ctdt.ten_chuong_trinh AS ten_ctdt,
                hp1.ten_mon AS hp1,
                hp2.ten_mon AS hp2
            ORDER BY hp1, hp2
        """

        with self.driver.session() as session:
            result = session.run(cypher, {"question": question})
            rows = [r.data() for r in result]

        if not rows:
            return []

        ctdt_name = rows[0].get("ten_ctdt", "Không rõ chương trình")

        tien_quyet_list = []
        seen = set()
        for r in rows:
            hp1 = (r.get("hp1") or "").strip()
            hp2 = (r.get("hp2") or "").strip()
            if not hp1 or not hp2:
                continue
            key = (hp1, hp2)
            if key in seen:
                continue
            seen.add(key)
            tien_quyet_list.append({
                "hoc_phan_1": hp1,
                "quan_he": "là học phần tiên quyết của",
                "hoc_phan_2": hp2
            })

        output = [{
            "ctdt": ctdt_name,
            "tien_quyet": tien_quyet_list
        }]

        return output
     # ==========================
    # Hỏi về học phần song hành của chương trình đào tạo
    # ==========================
    def get_song_hanh(self, question: str):

        logger.debug(f"🔎 get_song_hanh(): question='{question}'")

        # Trích tên CTĐT (nếu có)
        extracted_name = self.extract_ctdt_name(question)
        if extracted_name:
            question = extracted_name

        # --- Cypher tối ưu, không Cartesian explosion ---
        cypher = """
            CALL db.index.fulltext.queryNodes('ChuongTrinhDaoTao_full_text', $question)
            YIELD node AS ctdt
            WHERE toLower(ctdt.ten_chuong_trinh) CONTAINS toLower($question)

            MATCH (hp1)-[:THUOC]->(ctdt)
            MATCH (hp1)-[:LA_HOC_PHAN_SONG_HANH_VOI]->(hp2)
            MATCH (hp2)-[:THUOC]->(ctdt)

            OPTIONAL MATCH (hp1)-[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp3)
            OPTIONAL MATCH (hp2)-[:LA_HOC_PHAN_TIEN_QUYET_CUA]->(hp4)

            WITH DISTINCT 
                ctdt, hp1, hp2,
                collect(DISTINCT hp3.ten_mon) AS tien_quyet_hp1,
                collect(DISTINCT hp4.ten_mon) AS tien_quyet_hp2

            RETURN
                ctdt.ten_chuong_trinh AS ten_ctdt,
                hp1.ten_mon AS hp1,
                hp2.ten_mon AS hp2,
                tien_quyet_hp1,
                tien_quyet_hp2
            ORDER BY hp1, hp2
        """

        with self.driver.session() as session:
            result = session.run(cypher, {"question": question})
            rows = [r.data() for r in result]

        if not rows:
            return []

        # Tên CTĐT
        ctdt_name = rows[0].get("ten_ctdt", "Không rõ chương trình")

        song_hanh_list = []
        seen = set()

        for r in rows:
            hp1 = (r.get("hp1") or "").strip()
            hp2 = (r.get("hp2") or "").strip()

            if not hp1 or not hp2:
                continue

            key = (hp1, hp2)
            if key in seen:
                continue
            seen.add(key)

            # Danh sách tiên quyết (list)
            tq_hp1 = r.get("tien_quyet_hp1") or []
            tq_hp2 = r.get("tien_quyet_hp2") or []

            # Loại bỏ giá trị None + strip
            tq_hp1 = [x.strip() for x in tq_hp1 if x]
            tq_hp2 = [x.strip() for x in tq_hp2 if x]

            song_hanh_list.append({
                "hoc_phan_1": hp1,
                "quan_he": "là học phần song hành với",
                "hoc_phan_2": hp2,
                "tien_quyet_hp1": tq_hp1,
                "tien_quyet_hp2": tq_hp2
            })

        output = [{
            "ctdt": ctdt_name,
            "song_hanh": song_hanh_list
        }]

        return output




        


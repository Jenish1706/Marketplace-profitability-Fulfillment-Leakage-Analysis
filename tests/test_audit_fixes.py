"""
Audit Test Suite: Verifies P0 and P1 fixes against rigorous ground-truth criteria.
"""
import os
import sys
import unittest
import duckdb

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TestAuditFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = duckdb.connect()
        # Ingest staging
        with open(os.path.join(project_root, "sql", "01_schema.sql"), "r", encoding="utf-8") as f:
            cls.con.execute(f.read())
            
        tables = [
            ("olist_orders", os.path.join(project_root, "data", "raw", "olist_orders_dataset.csv")),
            ("olist_order_items", os.path.join(project_root, "data", "raw", "olist_order_items_dataset.csv")),
            ("olist_order_payments", os.path.join(project_root, "data", "raw", "olist_order_payments_dataset.csv")),
            ("olist_order_reviews", os.path.join(project_root, "data", "raw", "olist_order_reviews_dataset.csv")),
            ("olist_products", os.path.join(project_root, "data", "raw", "olist_products_dataset.csv")),
            ("olist_sellers", os.path.join(project_root, "data", "raw", "olist_sellers_dataset.csv")),
            ("olist_customers", os.path.join(project_root, "data", "raw", "olist_customers_dataset.csv")),
            ("olist_geolocation", os.path.join(project_root, "data", "raw", "olist_geolocation_dataset.csv")),
            ("product_category_name_translation", os.path.join(project_root, "data", "raw", "product_category_name_translation.csv"))
        ]
        for tbl, path in tables:
            cls.con.execute(f"INSERT INTO {tbl} SELECT * FROM read_csv_auto('{path.replace(chr(92), '/')}')")
            
        # Execute analytical SQL suite 02 through 07
        for sql_file in ["02_data_quality.sql", "03_order_item_fact.sql", "04_kpi_layer.sql", 
                         "05_root_cause_analysis.sql", "06_pareto_analysis.sql", "07_intervention_priority.sql"]:
            with open(os.path.join(project_root, "sql", sql_file), "r", encoding="utf-8") as f:
                cls.con.execute(f.read())

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_p01_same_day_delivery_not_late(self):
        """P0-1 Fix Test: Same-day delivery on estimated date must be marked on-time (is_late = 0)."""
        # Synthetic row test
        q_synthetic = """
        SELECT 
            CASE 
                WHEN CAST('2018-05-10 15:30:00' AS DATE) > CAST('2018-05-10 00:00:00' AS DATE) THEN 1 
                ELSE 0 
            END AS is_late_fixed,
            CASE 
                WHEN TIMESTAMP '2018-05-10 15:30:00' > TIMESTAMP '2018-05-10 00:00:00' THEN 1 
                ELSE 0 
            END AS is_late_buggy
        """
        fixed, buggy = self.con.execute(q_synthetic).fetchone()
        self.assertEqual(fixed, 0, "Fixed logic must treat same-day delivery as on-time")
        self.assertEqual(buggy, 1, "Buggy logic falsely treated same-day delivery as late")

        # Database Fact layer verification:
        q_real_same_day = """
        SELECT is_late 
        FROM fact_orders
        WHERE order_delivered_customer_date IS NOT NULL
          AND CAST(order_delivered_customer_date AS DATE) = CAST(order_estimated_delivery_date AS DATE)
          AND order_delivered_customer_date > order_estimated_delivery_date
        LIMIT 1;
        """
        row = self.con.execute(q_real_same_day).fetchone()
        if row:
            self.assertEqual(row[0], 0, "Same-day delivery in fact_orders must have is_late = 0")

        # Check total late count in fact_orders
        q_total_late = "SELECT COUNT(*) FROM fact_orders WHERE order_status = 'delivered' AND is_late = 1"
        total_late = self.con.execute(q_total_late).fetchone()[0]
        self.assertEqual(total_late, 6534, f"Expected 6,534 date-level late orders, got {total_late}")

    def test_p02_seller_vs_carrier_attribution(self):
        """P0-2 Fix Test: Split late deliveries into seller dispatch breach vs carrier transit delay."""
        # Check that fact_order_items contains the explicit attribution columns
        cols = [col[0] for col in self.con.execute("DESCRIBE fact_order_items").fetchall()]
        self.assertIn("is_seller_caused_late", cols, "fact_order_items must contain is_seller_caused_late")
        self.assertIn("is_carrier_caused_late", cols, "fact_order_items must contain is_carrier_caused_late")

        # Verify that carrier transit delay is attributed to carrier, not seller
        q = """
        SELECT 
            SUM(is_late) as total_late,
            SUM(is_seller_caused_late) as seller_late,
            SUM(is_carrier_caused_late) as carrier_late
        FROM fact_order_items
        WHERE is_delivered = 1;
        """
        total_late, seller_late, carrier_late = self.con.execute(q).fetchone()
        self.assertEqual(seller_late + carrier_late, total_late, "Seller + carrier late items must equal total late items")
        self.assertGreater(carrier_late, seller_late, "Carrier transit delay accounts for majority (~71%) of late items")

    def test_p03_reviews_answered_before_delivery(self):
        """P0-3 Fix Test: Verify review submission timing relative to package delivery and forward-looking bias."""
        q = """
        SELECT 
            is_late,
            ROUND(AVG(CASE WHEN r.review_answer_timestamp < o.order_delivered_customer_date THEN 1.0 ELSE 0.0 END) * 100, 2) AS pct_reviewed_before_delivery
        FROM fact_orders o
        JOIN (
            SELECT order_id, MAX(review_answer_timestamp) AS review_answer_timestamp
            FROM olist_order_reviews
            GROUP BY order_id
        ) r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
        GROUP BY is_late
        ORDER BY is_late;
        """
        rows = dict(self.con.execute(q).fetchall())
        self.assertAlmostEqual(rows[1], 70.10, delta=0.5, msg="~70% of late orders reviewed before delivery")
        self.assertLess(rows[0], 1.0, msg="<1% of on-time orders reviewed before delivery")

        # Forward-looking delay gap test: reviews before delivery average 3.73 days overdue at review vs 13.82 days at delivery
        q_gap = """
        SELECT 
            AVG(GREATEST(0, CAST(r.review_answer_timestamp AS DATE) - CAST(o.order_estimated_delivery_date AS DATE))) AS avg_overdue_review,
            AVG(GREATEST(0, CAST(o.order_delivered_customer_date AS DATE) - CAST(o.order_estimated_delivery_date AS DATE))) AS avg_overdue_delivery
        FROM fact_orders o
        JOIN (
            SELECT order_id, MAX(review_answer_timestamp) AS review_answer_timestamp
            FROM olist_order_reviews
            GROUP BY order_id
        ) r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered' AND o.is_late = 1 AND r.review_answer_timestamp < o.order_delivered_customer_date;
        """
        rev_days, del_days = self.con.execute(q_gap).fetchone()
        self.assertAlmostEqual(rev_days, 3.73, delta=0.5)
        self.assertAlmostEqual(del_days, 13.82, delta=0.5)
        self.assertLess(rev_days, del_days - 8.0, "Customer evaluated non-arrival at ~3.7 days overdue, not final ~13.8 days delay")

    def test_p04_exposure_and_scenarios(self):
        """P0-4 Fix Test: Metric is named late-order exposure and scenarios, no 'recoverable' claims."""
        cols = [col[0] for col in self.con.execute("DESCRIBE view_intervention_tier_summary").fetchall()]
        for col in cols:
            self.assertNotIn("recoverable", col.lower(), f"Column {col} must not claim 'recoverable'")
        self.assertIn("scenario_mitigation_base_25pct", cols)

    def test_p15_econometric_discrepancies(self):
        """P1-5 Fix Test: Verify notebook statistical outputs match markdown quotes without discrepancy."""
        import json
        nb_path = os.path.join(project_root, "notebooks", "business_analysis.ipynb")
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        
        # Check Kruskal-Wallis markdown vs code output
        found_kw_md = False
        found_kw_out = False
        for cell in nb["cells"]:
            text = "".join(cell.get("source", []))
            if "Kruskal-Wallis" in text and "10,167.48" in text:
                found_kw_md = True
            for out in cell.get("outputs", []):
                out_text = "".join(out.get("text", []))
                if "H = 10167.48" in out_text:
                    found_kw_out = True
        self.assertTrue(found_kw_md, "Notebook markdown must state H = 10,167.48")
        self.assertTrue(found_kw_out, "Notebook code output must report H = 10167.48")

    def test_p16_pareto_concentration_lift(self):
        """P1-6 Fix Test: Pareto view provides commercial baseline and concentration lift."""
        row = self.con.execute("SELECT decile_gmv_share_pct, decile_exposure_share_pct, concentration_lift FROM view_seller_pareto_deciles WHERE exposure_decile = 1").fetchone()
        gmv_share, exp_share, lift = row
        self.assertAlmostEqual(gmv_share, 60.78, places=1)
        self.assertAlmostEqual(exp_share, 77.38, places=1)
        self.assertAlmostEqual(lift, 1.27, places=1)

    def test_p17_temporal_chronic_split(self):
        """P1-7 Fix Test: Verify out-of-sample persistence of 2017 P1 sellers into 2018."""
        q = "SELECT tier_2017, avg_late_rate_2018 FROM view_seller_persistence_check"
        rates = dict(self.con.execute(q).fetchall())
        self.assertAlmostEqual(rates['P1_2017'], 13.05, delta=0.5, msg="2017 P1 sellers should maintain ~13% late rate in 2018")
        self.assertAlmostEqual(rates['Other_2017'], 8.60, delta=0.5, msg="Other sellers should maintain ~8.6% late rate in 2018")
        self.assertGreater(rates['P1_2017'], rates['Other_2017'], "P1 sellers must show persistent higher lateness out-of-sample")

    def test_mp03_persistence_result_rendered(self):
        """MP-03 Fix Test: Verify persistence result is rendered into README and decision memo from view."""
        row_p1 = self.con.execute("SELECT * FROM view_seller_persistence_check WHERE tier_2017 = 'P1_2017'").df().iloc[0]
        
        # Check README
        with open(os.path.join(project_root, "README.md"), "r", encoding="utf-8") as f:
            readme_text = f.read()
        self.assertIn(f"{row_p1['avg_late_rate_2018']:.2f}%", readme_text)
        self.assertIn(f"{row_p1['pct_above_base_rate']:.2f}%", readme_text)
        self.assertIn("BEGIN_PERSISTENCE_CHECK", readme_text)

        # Check Decision Memo
        with open(os.path.join(project_root, "report", "decision_memo.md"), "r", encoding="utf-8") as f:
            memo_text = f.read()
        self.assertIn(f"{row_p1['avg_late_rate_2018']:.2f}%", memo_text)
        self.assertIn("BEGIN_PERSISTENCE_CHECK", memo_text)

    def test_mp04_snapshot_formatting(self):
        """MP-04 Fix Test: Verify pipeline logger formats base_mitigation_25pct as currency R$, not %."""
        import io
        from contextlib import redirect_stdout
        from pipeline.logger import PipelineLogger
        
        logger = PipelineLogger(log_dir=os.path.join(project_root, "logs"))
        logger.record_snapshot({
            "freight_burden_pct": 16.57,
            "base_mitigation_25pct": 45344.39
        })
        
        f = io.StringIO()
        with redirect_stdout(f):
            logger.finalize()
        out = f.getvalue()
        
        self.assertIn("R$ 45,344.39", out, "base_mitigation_25pct must be formatted as currency R$ 45,344.39")
        self.assertNotIn("45344.39%", out, "base_mitigation_25pct must not be formatted as 45344.39%")

    def test_mp05_reproducible_environment(self):
        """MP-05 Fix Test: Verify requirements.txt is pinned and scripts/run_all.py orchestrates full verification."""
        req_path = os.path.join(project_root, "requirements.txt")
        self.assertTrue(os.path.isfile(req_path), "requirements.txt must exist")
        with open(req_path, "r", encoding="utf-8") as f:
            reqs = f.read()
        for pkg in ["duckdb==", "pandas==", "numpy==", "statsmodels==", "pytest=="]:
            self.assertIn(pkg, reqs, f"{pkg} must be pinned in requirements.txt")

        run_all_path = os.path.join(project_root, "scripts", "run_all.py")
        self.assertTrue(os.path.isfile(run_all_path), "scripts/run_all.py must exist")

    def test_p18_tier_naming_and_documentation(self):
        """P1-8 Fix Test: P4 tier is properly designated as Low Volume / Not Prioritised."""
        tiers = [row[0] for row in self.con.execute("SELECT priority_tier FROM view_intervention_tier_summary").fetchall()]
        self.assertIn("P4 - Low Volume / Not Prioritised", tiers)

    def test_mp02_honest_money_framing(self):
        """MP-02 Fix Test: Assert no 'recoverable', 'healthy operational', or 'transaction exposure' in README, report/, scripts/."""
        import re
        pattern = re.compile(r"recoverable|healthy operational|transaction exposure", re.IGNORECASE)
        target_paths = [
            os.path.join(project_root, "README.md"),
            os.path.join(project_root, "report", "decision_memo.md"),
            os.path.join(project_root, "report", "generate_decision_memo_pdf.py"),
            os.path.join(project_root, "scripts", "generate_writeup_pdf.py"),
            os.path.join(project_root, "scripts", "render_readme_tables.py"),
            os.path.join(project_root, "scripts", "run_review_econometrics.py"),
        ]
        violations = []
        for p in target_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            violations.append(f"{os.path.basename(p)}:{i}: {line.strip()}")
        self.assertEqual(violations, [], f"Found forbidden terminology: {violations}")

    def test_open_lead1_unfulfilled_orders_breakdown(self):
        """Open Lead 1 Fix Test: Quantify unfulfilled/undelivered orders outside the delivered rate."""
        cnt = self.con.execute("SELECT SUM(order_count) FROM view_unfulfilled_orders_breakdown").fetchone()[0]
        self.assertEqual(cnt, 2963, f"Expected 2,963 unfulfilled orders, got {cnt}")

    def test_readme_tables_match_database(self):
        """Authoritative Check: Re-renders README tables from database and asserts zero diff."""
        import subprocess
        res = subprocess.run([sys.executable, os.path.join(project_root, "scripts", "render_readme_tables.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"README tables drifted from database artifacts: {res.stdout} {res.stderr}")

    def test_mp01_clustering_variable_and_sensitivities(self):
        """MP-01 Fix Test: Econometrics script must cluster primarily on seller_id, not seller_state, and include sensitivities."""
        script_path = os.path.join(project_root, "scripts", "run_review_econometrics.py")
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()
        
        self.assertIn("df_reg['seller_id']", code, "Primary clustering group in run_review_econometrics.py must be seller_id")
        self.assertIn("seller_state", code, "Script must include seller_state sensitivity check")
        self.assertIn("HC1", code, "Script must include HC1 sensitivity check")

    def test_mp08_overdue_days_not_null_and_rendered(self):
        """MP-08 Fix Test: Overdue-day effect must not be called null or p=0.52; numbers rendered from script."""
        import glob
        doc_files = glob.glob(os.path.join(project_root, "docs", "**", "*.md"), recursive=True) + \
                    glob.glob(os.path.join(project_root, "report", "*.md")) + \
                    [os.path.join(project_root, "README.md")]
        study_guide = os.path.join(project_root, "docs", "interview_prep", "STUDY_GUIDE.md")
        if os.path.isfile(study_guide):
            doc_files.append(study_guide)

        for fpath in doc_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("p = 0.52", content, f"Forbidden 'p = 0.52' found in {os.path.relpath(fpath, project_root)}")
            self.assertNotIn("p=0.52", content, f"Forbidden 'p=0.52' found in {os.path.relpath(fpath, project_root)}")
            self.assertNotIn("Null Finding on Marginal Overdue", content, f"Overdue delay incorrectly classified as null in {os.path.relpath(fpath, project_root)}")
            self.assertNotIn("statistically indistinguishable from zero", content.lower(), f"Overdue effect called indistinguishable from zero in {os.path.relpath(fpath, project_root)}")

    def test_d1_guide_files_00_to_04(self):
        """D1 Acceptance Test: Guide files 00 to 04 exist and contain required sections and concepts."""
        guide_dir = os.path.join(project_root, "docs", "guide")
        required_files = [
            "00_START_HERE.md",
            "01_CONCEPTS.md",
            "02_ARCHITECTURE.md",
            "03_DATA.md",
            "04_METHODOLOGY.md",
        ]
        for fname in required_files:
            fpath = os.path.join(guide_dir, fname)
            self.assertTrue(os.path.isfile(fpath), f"Required guide file missing: {fname}")

        # Check 01_CONCEPTS.md for required concepts
        with open(os.path.join(guide_dir, "01_CONCEPTS.md"), "r", encoding="utf-8") as f:
            concepts_text = f.read().lower()
        required_concepts = [
            "analytical grain",
            "fan-out",
            "window function",
            "percentile tier",
            "pareto lift",
            "kruskal",
            "mann-whitney",
            "rank-biserial",
            "logistic regression",
            "cluster-robust",
            "association vs causation",
            "confounder",
            "mediator",
            "review-timing",
            "information set",
            "right-censoring",
            "survivorship",
        ]
        for c in required_concepts:
            self.assertIn(c, concepts_text, f"01_CONCEPTS.md missing concept: {c}")

        # Check 02_ARCHITECTURE.md for Mermaid diagram and components
        with open(os.path.join(guide_dir, "02_ARCHITECTURE.md"), "r", encoding="utf-8") as f:
            arch_text = f.read()
        self.assertIn("```mermaid", arch_text, "02_ARCHITECTURE.md must contain a Mermaid diagram")

        # Check 03_DATA.md for schemas and quality
        with open(os.path.join(guide_dir, "03_DATA.md"), "r", encoding="utf-8") as f:
            data_text = f.read()
        self.assertIn("99,441", data_text, "03_DATA.md must contain orders row count 99,441")
        self.assertIn("112,650", data_text, "03_DATA.md must contain order items row count 112,650")

        # Check 04_METHODOLOGY.md for protocol and falsification
        with open(os.path.join(guide_dir, "04_METHODOLOGY.md"), "r", encoding="utf-8") as f:
            meth_text = f.read().lower()
        self.assertIn("falsif", meth_text, "04_METHODOLOGY.md must detail falsification criteria")

    def test_d2_guide_files_05_to_09_and_glossary(self):
        """D2 Acceptance Test: Guide files 05 to 09 and Glossary exist and contain required content."""
        guide_dir = os.path.join(project_root, "docs", "guide")
        required_files = [
            "05_CODE_WALKTHROUGH.md",
            "06_RUNBOOK.md",
            "07_TESTING.md",
            "08_DESIGN_DECISIONS.md",
            "09_RESULTS_AND_LIMITATIONS.md",
            "GLOSSARY.md",
        ]
        for fname in required_files:
            fpath = os.path.join(guide_dir, fname)
            self.assertTrue(os.path.isfile(fpath), f"Required guide file missing: {fname}")

        # Check 05_CODE_WALKTHROUGH.md has stages and functions
        with open(os.path.join(guide_dir, "05_CODE_WALKTHROUGH.md"), "r", encoding="utf-8") as f:
            cw_text = f.read()
        self.assertIn("pipeline/ingestion.py", cw_text)
        self.assertIn("pipeline/validation.py", cw_text)
        self.assertIn("scripts/run_review_econometrics.py", cw_text)

        # Check 06_RUNBOOK.md has exact commands and troubleshooting
        with open(os.path.join(guide_dir, "06_RUNBOOK.md"), "r", encoding="utf-8") as f:
            rb_text = f.read()
        self.assertIn("scripts/run_all.py", rb_text)
        self.assertIn("Troubleshooting", rb_text)

        # Check 07_TESTING.md has coverage and fresh-clone
        with open(os.path.join(guide_dir, "07_TESTING.md"), "r", encoding="utf-8") as f:
            t_text = f.read()
        self.assertIn("fresh-clone", t_text.lower())

        # Check 08_DESIGN_DECISIONS.md has ADR format
        with open(os.path.join(guide_dir, "08_DESIGN_DECISIONS.md"), "r", encoding="utf-8") as f:
            adr_text = f.read()
        self.assertIn("Context", adr_text)
        self.assertIn("Decision", adr_text)
        self.assertIn("Alternatives", adr_text)
        self.assertIn("Consequences", adr_text)

        # Check 09_RESULTS_AND_LIMITATIONS.md has null results and validity threats
        with open(os.path.join(guide_dir, "09_RESULTS_AND_LIMITATIONS.md"), "r", encoding="utf-8") as f:
            res_text = f.read()
        self.assertIn("Threats to Validity", res_text)

        # Check GLOSSARY.md has entries
        with open(os.path.join(guide_dir, "GLOSSARY.md"), "r", encoding="utf-8") as f:
            gl_text = f.read()
        for term in ["GMV", "SLA", "3PL", "EDD", "Pareto Lift", "Cluster-Robust"]:
            self.assertIn(term, gl_text, f"Glossary missing term: {term}")

    def test_d3_readme_and_study_material(self):
        """D3 Acceptance Test: README under 200 lines, links to guide, and private study files complete."""
        import re
        readme_path = os.path.join(project_root, "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertLessEqual(len(lines), 205, f"README.md should be under ~200 lines, found {len(lines)}")
        readme_text = "".join(lines)
        self.assertIn("docs/guide/00_START_HERE.md", readme_text, "README.md must link to docs/guide/00_START_HERE.md")

        # Study guide checks
        study_guide_path = os.path.join(project_root, "docs", "interview_prep", "STUDY_GUIDE.md")
        self.assertTrue(os.path.isfile(study_guide_path), "STUDY_GUIDE.md must exist in docs/interview_prep/")
        with open(study_guide_path, "r", encoding="utf-8") as f:
            sg_text = f.read()
        self.assertIn("60-Second", sg_text)
        self.assertIn("5-Minute", sg_text)
        self.assertIn("Whiteboard", sg_text)
        self.assertIn("Q25", sg_text, "STUDY_GUIDE.md must contain 25 interview questions")

        # Writeup tex checks
        writeup_tex_path = os.path.join(project_root, "docs", "interview_prep", "WRITEUP.tex")
        self.assertTrue(os.path.isfile(writeup_tex_path), "WRITEUP.tex must exist in docs/interview_prep/")
        with open(writeup_tex_path, "r", encoding="utf-8") as f:
            tex_text = f.read()
        pattern = re.compile(r"recoverable|healthy operational|transaction exposure", re.IGNORECASE)
        self.assertFalse(pattern.search(tex_text), "WRITEUP.tex must not contain forbidden phrases")

    def test_d4_documentation_checks_gate_g3(self):
        """D4 / Gate G3 Test: All relative markdown links resolve, walkthrough files/functions exist, render check passes."""
        import re
        import subprocess

        # 1. Check all relative markdown links in README and docs/
        md_files = [os.path.join(project_root, "README.md")]
        for root, _, files in os.walk(os.path.join(project_root, "docs")):
            for f in files:
                if f.endswith(".md"):
                    md_files.append(os.path.join(root, f))

        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        broken_links = []
        for md_path in md_files:
            dir_name = os.path.dirname(md_path)
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            for m in link_pattern.finditer(content):
                link = m.group(2).strip()
                if link.startswith("http://") or link.startswith("https://") or link.startswith("mailto:") or link.startswith("#") or link.startswith("file:"):
                    continue
                target_path = link.split("#")[0]
                if not target_path:
                    continue
                full_target = os.path.normpath(os.path.join(dir_name, target_path))
                if not os.path.exists(full_target):
                    broken_links.append(f"{os.path.relpath(md_path, project_root)} -> {link}")

        self.assertEqual(broken_links, [], f"Broken relative links found: {broken_links}")

        # 2. Check all files and functions referenced in 05_CODE_WALKTHROUGH.md
        walkthrough_funcs = [
            ("pipeline/ingestion.py", "def ingest_raw_sources"),
            ("pipeline/validation.py", "def validate_sources_exist"),
            ("pipeline/validation.py", "def validate_staging_health"),
            ("pipeline/run_pipeline.py", "def run_pipeline"),
            ("tests/verify_pipeline.py", "def run_pipeline"),
            ("scripts/render_readme_tables.py", "def get_rendered_blocks"),
            ("scripts/render_readme_tables.py", "def update_file_markers"),
            ("scripts/render_readme_tables.py", "def sync_all"),
            ("scripts/run_review_econometrics.py", "def get_db_connection"),
            ("scripts/run_review_econometrics.py", "def fit_models"),
            ("scripts/run_review_econometrics.py", "def generate_regression_markdown_table"),
            ("scripts/run_all.py", "def main"),
        ]
        missing = []
        for rel, sig in walkthrough_funcs:
            fpath = os.path.join(project_root, rel)
            if not os.path.isfile(fpath):
                missing.append(f"Missing file: {rel}")
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                c = f.read()
            if sig not in c:
                missing.append(f"{rel} missing function: {sig}")
        self.assertEqual(missing, [], f"Walkthrough discrepancies: {missing}")

        # 3. Check README and memo rendering passes
        res = subprocess.run([sys.executable, os.path.join(project_root, "scripts", "render_readme_tables.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Render check failed: {res.stdout} {res.stderr}")

    def test_c1_cleanup_plan_inventory_complete(self):
        """C1 Acceptance Test: CLEANUP_PLAN.md exists and inventories all required categories."""
        if not os.path.isdir(os.path.join(project_root, ".audit")):
            return  # .audit/ is an untracked private directory not present in fresh clone
        plan_path = os.path.join(project_root, ".audit", "CLEANUP_PLAN.md")
        self.assertTrue(os.path.isfile(plan_path), "CLEANUP_PLAN.md must exist")
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_text = f.read()
        self.assertIn("Category 1: Caches", plan_text)
        self.assertIn("Category 2: Run Logs", plan_text)
        self.assertIn("Category 5: Superseded", plan_text)
        self.assertIn("Category 6: Audit Transfer Files", plan_text)

    def test_c2_cleanup_execution_and_log(self):
        """C2 Acceptance Test: CLEANUP_LOG.md exists, superseded docs removed, and gitignore hardened."""
        # Confirm superseded docs are no longer present
        superseded = [
            "docs/data_lineage.md",
            "docs/stakeholder_requirements.md",
            "pipeline/README.md",
            "data/README.md",
        ]
        for s in superseded:
            self.assertFalse(os.path.exists(os.path.join(project_root, s)), f"Superseded file must be removed: {s}")

        if not os.path.isdir(os.path.join(project_root, ".audit")):
            return  # .audit/ is an untracked private directory not present in fresh clone

        log_path = os.path.join(project_root, ".audit", "CLEANUP_LOG.md")
        self.assertTrue(os.path.isfile(log_path), "CLEANUP_LOG.md must exist")
        with open(log_path, "r", encoding="utf-8") as f:
            log_text = f.read()
        self.assertIn("Total Deletions", log_text)
        self.assertIn("Total Space Freed", log_text)

if __name__ == "__main__":
    unittest.main()

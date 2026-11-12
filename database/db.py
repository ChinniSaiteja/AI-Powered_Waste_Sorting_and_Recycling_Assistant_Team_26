"""
Subsystem 4 - Data Management & AI Guidance
Owner: Ha Le Thu

DatabaseManager: the ONLY place in the project that contains SQL.
Other subsystems call its methods and receive plain Python dicts / objects.

Supports two engines, chosen in .env (no code change needed):
    DB_ENGINE=sqlite   -> file database/waste.db, nothing to install (default)
    DB_ENGINE=mysql    -> MySQL server, needs DB_HOST / DB_USER / DB_PASSWORD / DB_NAME

Usage (e.g. in the Flask app):
    from database.db import DatabaseManager
    db = DatabaseManager()
    db.initialize()                       # creates tables + loads Dortmund rules once
    rule = db.get_rule("glass jar")       # -> dict or None
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from database.exceptions import (DatabaseConnectionError, DataManagementError,
                                 InvalidDataError, ItemNotFoundError)
from database.models import DisposalRule, WasteCategory, WasteItem

try:  # optional: read settings from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "database" / "waste.db"
DEFAULT_SEED_FILE = BASE_DIR / "data" / "waste_guidance.json"
SCHEMA_FILES = {
    "sqlite": BASE_DIR / "database" / "schema_sqlite.sql",
    "mysql": BASE_DIR / "database" / "schema_mysql.sql",
}


class DatabaseManager:
    """Creates the database, loads seed data and answers queries for all subsystems."""

    ALLOWED_ENGINES = ("sqlite", "mysql")
    ALLOWED_STATUS = ("completed", "uncertain", "failed")

    # 1. Constructor
    def __init__(self, engine: str | None = None, db_path: str | None = None):
        self.__engine = None
        self.engine = engine or os.getenv("DB_ENGINE", "sqlite")
        self.db_path = db_path or os.getenv("DB_PATH", str(DEFAULT_SQLITE_PATH))
        self.__mysql_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        self.__db_name = os.getenv("DB_NAME", "waste_db")

    # 3. Getters & setters
    @property
    def engine(self) -> str:
        return self.__engine

    @engine.setter
    def engine(self, value: str) -> None:
        value = str(value).strip().lower()
        if value not in self.ALLOWED_ENGINES:
            raise InvalidDataError("DB_ENGINE", value, f"must be one of {self.ALLOWED_ENGINES}")
        self.__engine = value

    @property
    def db_path(self) -> str:
        return self.__db_path

    @db_path.setter
    def db_path(self, value: str) -> None:
        if not value:
            raise InvalidDataError("db_path", value, "must not be empty")
        path = Path(value)
        # a relative path (e.g. DB_PATH=database/waste.db in .env) always means the project
        # folder, so the Flask app and the demo scripts use the same file from any folder
        self.__db_path = str(path if path.is_absolute() else BASE_DIR / path)

    @property
    def db_name(self) -> str:
        return self.__db_name

    # ------------------------------------------------------------------
    # Internal helpers (private)
    # ------------------------------------------------------------------
    def __sql(self, query: str) -> str:
        """Queries are written with '?' placeholders; MySQL needs '%s'."""
        return query.replace("?", "%s") if self.__engine == "mysql" else query

    def __insert_ignore(self) -> str:
        return "INSERT IGNORE" if self.__engine == "mysql" else "INSERT OR IGNORE"

    @contextmanager
    def __connect(self):
        """Open a connection, give back a cursor that returns dict rows, commit at the end.

        Error handling (Home Assignment 4):
          - connection problems  -> DatabaseConnectionError
          - broken constraints   -> InvalidDataError (e.g. duplicate feedback, unknown id)
          - any error            -> rollback, so the database never keeps half-saved data
        """
        try:
            if self.__engine == "sqlite":
                Path(self.__db_path).parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(self.__db_path)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
            else:
                import mysql.connector  # only needed when DB_ENGINE=mysql
                conn = mysql.connector.connect(database=self.__db_name, **self.__mysql_config)
                cursor = conn.cursor(dictionary=True)
        except Exception as error:
            raise DatabaseConnectionError(self.__engine, error) from error
        try:
            yield cursor
            conn.commit()
        except DataManagementError:
            conn.rollback()
            raise
        except Exception as error:
            conn.rollback()
            if "IntegrityError" in type(error).__name__:
                raise InvalidDataError("record", None, f"violates a database rule: {error}") from error
            raise
        finally:
            cursor.close()
            conn.close()

    def __create_mysql_database(self) -> None:
        import mysql.connector
        try:
            conn = mysql.connector.connect(**self.__mysql_config)
        except Exception as error:
            raise DatabaseConnectionError("mysql", error) from error
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{self.__db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.close()
        conn.close()

    @staticmethod
    def __read_statements(schema_file: Path) -> list[str]:
        """Split a .sql file into single statements (comments removed)."""
        lines = [ln for ln in schema_file.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().startswith("--")]
        return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

    # ------------------------------------------------------------------
    # 2. Initialisation methods
    # ------------------------------------------------------------------
    def initialize(self, seed_file: str | Path = DEFAULT_SEED_FILE) -> int:
        """Create all 8 tables (if missing) and load the rules the first time.

        Returns the number of rules loaded (0 if the data was already there).
        """
        if self.__engine == "mysql":
            self.__create_mysql_database()
        with self.__connect() as cur:
            for statement in self.__read_statements(SCHEMA_FILES[self.__engine]):
                cur.execute(statement)
            cur.execute("SELECT COUNT(*) AS n FROM waste_items")
            already_seeded = cur.fetchone()["n"] > 0
        if already_seeded:
            return 0
        return self.seed(self.load_guidance_file(seed_file))

    @staticmethod
    def load_guidance_file(path: str | Path = DEFAULT_SEED_FILE) -> list[DisposalRule]:
        """Read waste_guidance.json and turn every entry into model objects."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise ItemNotFoundError("seed file", str(path)) from None
        except json.JSONDecodeError as error:
            raise InvalidDataError("seed file", str(path), f"is not valid JSON ({error})") from None
        region = data.get("region", DisposalRule.DEFAULT_REGION)
        categories = {c["name"]: WasteCategory.from_dict(c) for c in data["categories"]}
        rules = []
        for entry in data["items"]:
            item = WasteItem.from_dict(entry, categories[entry["category"]])
            rules.append(DisposalRule.from_dict(entry, item, region=region))
        return rules

    def seed(self, rules: list[DisposalRule]) -> int:
        """Insert categories, items and rules. Existing rows are skipped."""
        with self.__connect() as cur:
            for rule in rules:
                category = rule.item.category
                cur.execute(self.__sql(
                    f"{self.__insert_ignore()} INTO waste_categories (name, description) VALUES (?, ?)"),
                    (category.name, category.description))
                cur.execute(self.__sql("SELECT id FROM waste_categories WHERE name = ?"),
                            (category.name,))
                category.id = cur.fetchone()["id"]

                cur.execute(self.__sql(
                    f"{self.__insert_ignore()} INTO waste_items (category_id, label, is_deposit) "
                    "VALUES (?, ?, ?)"),
                    (category.id, rule.item.label, rule.item.is_deposit))
                cur.execute(self.__sql("SELECT id FROM waste_items WHERE label = ?"),
                            (rule.item.label,))
                rule.item.id = cur.fetchone()["id"]

                cur.execute(self.__sql(
                    f"{self.__insert_ignore()} INTO disposal_rules "
                    "(item_id, region, bin_type, instruction) VALUES (?, ?, ?, ?)"),
                    (rule.item.id, rule.region, rule.bin_type, rule.instruction))
        return len(rules)

    # ------------------------------------------------------------------
    # Public API for the other subsystems
    # ------------------------------------------------------------------
    def get_rule(self, label: str, region: str = DisposalRule.DEFAULT_REGION) -> dict | None:
        """Backend: disposal guidance for a classifier label, or None if unknown."""
        with self.__connect() as cur:
            cur.execute(self.__sql("""
                SELECT w.id AS item_id, w.label, w.is_deposit, c.id AS category_id,
                       c.name AS category, c.description, r.id AS rule_id,
                       r.region, r.bin_type, r.instruction
                FROM waste_items w
                JOIN waste_categories c ON c.id = w.category_id
                JOIN disposal_rules r   ON r.item_id = w.id
                WHERE w.label = ? AND r.region = ?
            """), (label.strip().lower(), region.strip().title()))
            row = cur.fetchone()
        if row is None:
            return None
        category = WasteCategory(row["category_id"], row["category"], row["description"])
        item = WasteItem(row["item_id"], row["label"], category, bool(row["is_deposit"]))
        rule = DisposalRule(row["rule_id"], item, row["bin_type"], row["instruction"], row["region"])
        return rule.to_dict()

    def require_rule(self, label: str, region: str = DisposalRule.DEFAULT_REGION) -> dict:
        """Like get_rule(), but raises ItemNotFoundError instead of returning None."""
        rule = self.get_rule(label, region)
        if rule is None:
            raise ItemNotFoundError("disposal rule", label.strip().lower(), region.strip().title())
        return rule

    def get_all_items(self) -> list[WasteItem]:
        """All known labels (useful for the classifier team and for tests)."""
        with self.__connect() as cur:
            cur.execute("""
                SELECT w.id, w.label, w.is_deposit, c.id AS category_id, c.name, c.description
                FROM waste_items w JOIN waste_categories c ON c.id = w.category_id
                ORDER BY c.name, w.label
            """)
            rows = cur.fetchall()
        return [
            WasteItem(r["id"], r["label"],
                      WasteCategory(r["category_id"], r["name"], r["description"]),
                      bool(r["is_deposit"]))
            for r in rows
        ]

    def save_classification(self, label: str, confidence: float | None = None,
                            status: str = "completed",
                            region: str = DisposalRule.DEFAULT_REGION,
                            created_at: str | None = None) -> int:
        """Backend: store one classification result. Returns the new id.

        created_at ('YYYY-MM-DD HH:MM:SS') is optional and only used for demo data.
        """
        label = str(label or "").strip().lower()
        if not label:
            raise InvalidDataError("label", label, "must not be empty")
        if status not in self.ALLOWED_STATUS:
            raise InvalidDataError("status", status, f"must be one of {self.ALLOWED_STATUS}")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                raise InvalidDataError("confidence", confidence, "must be a number") from None
            if not 0.0 <= confidence <= 1.0:
                raise InvalidDataError("confidence", confidence, "must be between 0 and 1")
        with self.__connect() as cur:
            cur.execute(self.__sql("SELECT id FROM waste_items WHERE label = ?"), (label,))
            row = cur.fetchone()
            item_id = row["id"] if row else None
            if created_at:
                cur.execute(self.__sql("""
                    INSERT INTO classifications
                        (item_id, predicted_label, confidence, status, region, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """), (item_id, label, confidence, status, region.strip().title(), created_at))
            else:
                cur.execute(self.__sql("""
                    INSERT INTO classifications (item_id, predicted_label, confidence, status, region)
                    VALUES (?, ?, ?, ?, ?)
                """), (item_id, label, confidence, status, region.strip().title()))
            return cur.lastrowid

    def save_feedback(self, classification_id: int, is_correct: bool,
                      correct_label: str | None = None) -> None:
        """Backend: store the answer of the 'Wrong result?' button."""
        with self.__connect() as cur:
            cur.execute(self.__sql("SELECT id FROM classifications WHERE id = ?"), (classification_id,))
            if cur.fetchone() is None:
                raise ItemNotFoundError("classification", classification_id)
            cur.execute(self.__sql("""
                INSERT INTO user_feedback (classification_id, is_correct, correct_label)
                VALUES (?, ?, ?)
            """), (classification_id, bool(is_correct),
                   correct_label.strip().lower() if correct_label else None))

    def get_classification_records(self, region: str | None = DisposalRule.DEFAULT_REGION,
                                   limit: int = 50) -> list[dict]:
        """Dashboard: latest classification records, newest first (region=None -> all regions).

        Each record joins classifications + waste_items + categories + rules + AI cache:
            id, waste_name, label, category, confidence, bin_type, disposal_instruction,
            explanation, is_deposit, status, region, created_at
        """
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise InvalidDataError("limit", limit, "must be a number") from None
        if not 1 <= limit <= 1000:
            raise InvalidDataError("limit", limit, "must be between 1 and 1000")
        where, params = self.__region_filter(region)
        with self.__connect() as cur:
            cur.execute(self.__sql(f"""
                SELECT cl.id, cl.predicted_label, cl.confidence, cl.status, cl.region,
                       cl.created_at, c.name AS category, w.is_deposit,
                       r.bin_type, r.instruction,
                       (SELECT g.answer FROM ai_guidance g
                        WHERE g.item_id = cl.item_id AND g.question IS NULL
                        ORDER BY g.id DESC LIMIT 1) AS explanation
                FROM classifications cl
                LEFT JOIN waste_items w      ON w.id = cl.item_id
                LEFT JOIN waste_categories c ON c.id = w.category_id
                LEFT JOIN disposal_rules r   ON r.item_id = cl.item_id AND r.region = cl.region
                {where}
                ORDER BY cl.created_at DESC, cl.id DESC
                LIMIT ?
            """), params + [limit])
            rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "waste_name": r["predicted_label"].capitalize(),
                "label": r["predicted_label"],
                "category": r["category"],              # None if the label is unknown
                "confidence": r["confidence"],
                "bin_type": r["bin_type"],
                "disposal_instruction": r["instruction"],
                "explanation": r["explanation"],
                "is_deposit": bool(r["is_deposit"]) if r["is_deposit"] is not None else False,
                "status": r["status"],
                "region": r["region"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]

    @staticmethod
    def __region_filter(region: str | None) -> tuple[str, list]:
        """WHERE clause for one region, or for all regions when region is None."""
        if region is None:
            return "WHERE 1 = 1", []
        return "WHERE cl.region = ?", [region.strip().title()]

    def get_stats(self, region: str | None = DisposalRule.DEFAULT_REGION,
                  date_from: str | None = None, date_to: str | None = None,
                  top_n: int = 5) -> dict:
        """Dashboard: aggregated statistics. Dates as 'YYYY-MM-DD' (optional).

        region=None -> all regions. Keys: region, total_items, by_category,
        category_percentages, recycling_rate, per_day, top_items, region_counts,
        uncertain_count, wrong_feedback_count
        """
        where, params = self.__region_filter(region)
        if date_from:
            where += " AND DATE(cl.created_at) >= ?"
            params.append(date_from)
        if date_to:
            where += " AND DATE(cl.created_at) <= ?"
            params.append(date_to)

        with self.__connect() as cur:
            cur.execute(self.__sql(f"""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN cl.status = 'uncertain' THEN 1 ELSE 0 END) AS uncertain
                FROM classifications cl {where}
            """), params)
            totals = cur.fetchone()

            cur.execute(self.__sql(f"""
                SELECT c.name AS category, COUNT(*) AS n
                FROM classifications cl
                JOIN waste_items w      ON w.id = cl.item_id
                JOIN waste_categories c ON c.id = w.category_id
                {where}
                GROUP BY c.name
            """), params)
            by_category = {r["category"]: int(r["n"]) for r in cur.fetchall()}

            cur.execute(self.__sql(f"""
                SELECT DATE(cl.created_at) AS day, COUNT(*) AS n
                FROM classifications cl {where}
                GROUP BY DATE(cl.created_at)
                ORDER BY day
            """), params)
            per_day = [{"date": str(r["day"]), "count": int(r["n"])} for r in cur.fetchall()]

            cur.execute(self.__sql(f"""
                SELECT COUNT(*) AS n
                FROM user_feedback f
                JOIN classifications cl ON cl.id = f.classification_id
                {where} AND f.is_correct = ?
            """), params + [False])
            wrong = cur.fetchone()["n"]

            cur.execute(self.__sql(f"""
                SELECT cl.predicted_label AS label, COUNT(*) AS n
                FROM classifications cl {where}
                GROUP BY cl.predicted_label
                ORDER BY n DESC, cl.predicted_label
                LIMIT ?
            """), params + [int(top_n)])
            top_items = [{"label": r["label"], "waste_name": r["label"].capitalize(),
                          "count": int(r["n"])} for r in cur.fetchall()]

            cur.execute(self.__sql(f"""
                SELECT cl.region, COUNT(*) AS n
                FROM classifications cl {where}
                GROUP BY cl.region
                ORDER BY n DESC
            """), params)
            region_counts = {r["region"]: int(r["n"]) for r in cur.fetchall()}

        total = int(totals["total"] or 0)
        counts = {name: by_category.get(name, 0) for name in WasteCategory.ALLOWED_NAMES}
        known = sum(counts.values())   # unknown labels have no category
        recyclable = by_category.get("recyclable", 0)
        return {
            "region": region.strip().title() if region else "All regions",
            "total_items": total,
            "by_category": counts,
            "category_percentages": {name: round(100 * n / known, 1) if known else 0.0
                                     for name, n in counts.items()},
            "recycling_rate": round(recyclable / total, 3) if total else 0.0,
            "per_day": per_day,
            "top_items": top_items,
            "region_counts": region_counts,
            "uncertain_count": int(totals["uncertain"] or 0),
            "wrong_feedback_count": int(wrong or 0),
        }

    # ------------------------------------------------------------------
    # AI guidance support (used by GuidanceService, capstone)
    # ------------------------------------------------------------------
    def get_cached_guidance(self, label: str, question: str | None = None) -> str | None:
        """Return a stored AI answer for this item, or None.

        question=None -> the explanation of the item; otherwise the answer to that question.
        """
        question_filter = "g.question IS NULL" if question is None else "g.question = ?"
        params = [label.strip().lower()] + ([] if question is None else [question.strip()])
        with self.__connect() as cur:
            cur.execute(self.__sql(f"""
                SELECT g.answer FROM ai_guidance g
                JOIN waste_items w ON w.id = g.item_id
                WHERE w.label = ? AND {question_filter}
                ORDER BY g.id DESC
            """), params)
            row = cur.fetchone()
        return row["answer"] if row else None

    def save_guidance(self, label: str, answer: str, question: str | None = None) -> bool:
        """Cache an AI explanation (question=None) or an answer to a user question.

        Returns False if the label is not in waste_items.
        """
        if not str(answer or "").strip():
            raise InvalidDataError("answer", answer, "must not be empty")
        with self.__connect() as cur:
            cur.execute(self.__sql("SELECT id FROM waste_items WHERE label = ?"),
                        (label.strip().lower(),))
            row = cur.fetchone()
            if row is None:
                return False
            cur.execute(self.__sql("INSERT INTO ai_guidance (item_id, question, answer) VALUES (?, ?, ?)"),
                        (row["id"], question.strip() if question else None, answer.strip()))
        return True

    def get_ai_usage(self, usage_date: str) -> int:
        """Number of AI calls on one day ('YYYY-MM-DD')."""
        with self.__connect() as cur:
            cur.execute(self.__sql("SELECT request_count FROM ai_usage_log WHERE usage_date = ?"),
                        (usage_date,))
            row = cur.fetchone()
        return int(row["request_count"]) if row else 0

    def increment_ai_usage(self, usage_date: str) -> int:
        """Add 1 to today's AI counter and return the new value."""
        with self.__connect() as cur:
            cur.execute(self.__sql(
                f"{self.__insert_ignore()} INTO ai_usage_log (usage_date, request_count) VALUES (?, 0)"),
                (usage_date,))
            cur.execute(self.__sql(
                "UPDATE ai_usage_log SET request_count = request_count + 1 WHERE usage_date = ?"),
                (usage_date,))
        return self.get_ai_usage(usage_date)

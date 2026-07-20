from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    db_path = Path(db_path)
    if readonly:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def query_summary(conn: sqlite3.Connection, as_of_date: str) -> dict:
    fact = conn.execute(
        """
        SELECT COUNT(*) AS document_count,
               COALESCE(SUM(open_balance_amount), 0) AS total_balance,
               COALESCE(SUM(line_count), 0) AS line_count
        FROM ar_balance_facts
        WHERE as_of_date = ?
        """,
        (as_of_date,),
    ).fetchone()
    object_counts = rows(
        conn.execute(
            """
            SELECT object_level, object_type, COUNT(*) AS count
            FROM finance_business_objects
            GROUP BY object_level, object_type
            ORDER BY object_level, object_type
            """
        )
    )
    entities = conn.execute("SELECT COUNT(*) AS count FROM finance_entities").fetchone()["count"]
    return {
        "as_of_date": as_of_date,
        "groups": conn.execute("SELECT COUNT(*) AS count FROM finance_groups").fetchone()["count"],
        "entities": entities,
        "object_counts": object_counts,
        "document_facts": fact["document_count"],
        "fact_lines": fact["line_count"],
        "total_balance": round(float(fact["total_balance"]), 2),
    }


def query_entity_balances(conn: sqlite3.Connection, as_of_date: str) -> list[dict]:
    return rows(
        conn.execute(
            """
            SELECT e.entity_name,
                   COUNT(f.fact_id) AS document_count,
                   COALESCE(SUM(f.line_count), 0) AS line_count,
                   ROUND(COALESCE(SUM(f.open_balance_amount), 0), 2) AS balance
            FROM finance_entities e
            LEFT JOIN ar_balance_facts f ON f.entity_id = e.entity_id AND f.as_of_date = ?
            GROUP BY e.entity_id, e.entity_name
            ORDER BY balance DESC, e.entity_name
            """,
            (as_of_date,),
        )
    )


def query_counterparty_balances(conn: sqlite3.Connection, as_of_date: str) -> list[dict]:
    return rows(
        conn.execute(
            """
            SELECT e.entity_name,
                   cp.customer_name,
                   COUNT(f.fact_id) AS document_count,
                   ROUND(COALESCE(SUM(f.open_balance_amount), 0), 2) AS balance
            FROM finance_business_objects cp
            JOIN finance_entities e ON e.entity_id = cp.entity_id
            LEFT JOIN finance_business_objects doc ON doc.parent_object_id = cp.object_id AND doc.object_type = 'document'
            LEFT JOIN ar_balance_facts f ON f.object_id = doc.object_id AND f.as_of_date = ?
            WHERE cp.object_type = 'counterparty'
            GROUP BY cp.object_id, e.entity_name, cp.customer_name
            ORDER BY balance DESC, e.entity_name, cp.customer_name
            """,
            (as_of_date,),
        )
    )


def query_document_balances(conn: sqlite3.Connection, as_of_date: str) -> list[dict]:
    return rows(
        conn.execute(
            """
            SELECT e.entity_name,
                   doc.customer_name,
                   doc.source_doc_no,
                   f.line_count,
                   ROUND(f.open_balance_amount, 2) AS balance
            FROM ar_balance_facts f
            JOIN finance_business_objects doc ON doc.object_id = f.object_id
            JOIN finance_entities e ON e.entity_id = f.entity_id
            WHERE f.as_of_date = ?
            ORDER BY balance DESC, e.entity_name, doc.customer_name, doc.source_doc_no
            """,
            (as_of_date,),
        )
    )


def query_document_lines(
    conn: sqlite3.Connection,
    as_of_date: str,
    *,
    entity_name: str,
    customer_name: str,
    source_doc_no: str,
) -> list[dict]:
    return rows(
        conn.execute(
            """
            SELECT e.entity_name,
                   l.customer_name,
                   l.source_doc_no,
                   l.source_row,
                   l.ar_amount,
                   l.posting_date,
                   l.writeoff_amount,
                   l.ar_balance,
                   l.description
            FROM ar_balance_fact_lines l
            JOIN ar_balance_facts f ON f.fact_id = l.fact_id
            JOIN finance_entities e ON e.entity_id = l.entity_id
            WHERE f.as_of_date = ?
              AND e.entity_name = ?
              AND l.customer_name = ?
              AND l.source_doc_no = ?
            ORDER BY l.source_row
            """,
            (as_of_date, entity_name, customer_name, source_doc_no),
        )
    )


def verify_consistency(conn: sqlite3.Connection, as_of_date: str) -> dict:
    summary_total = query_summary(conn, as_of_date)["total_balance"]
    entity_total = round(sum(float(row["balance"]) for row in query_entity_balances(conn, as_of_date)), 2)
    counterparty_total = round(sum(float(row["balance"]) for row in query_counterparty_balances(conn, as_of_date)), 2)
    document_total = round(sum(float(row["balance"]) for row in query_document_balances(conn, as_of_date)), 2)
    q_blank_brought_lines = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM ar_balance_fact_lines
        WHERE ar_balance = 0
          AND fact_id IN (SELECT fact_id FROM ar_balance_facts WHERE as_of_date = ?)
        """,
        (as_of_date,),
    ).fetchone()["count"]
    ok = summary_total == entity_total == counterparty_total == document_total
    return {
        "ok": ok,
        "as_of_date": as_of_date,
        "totals": {
            "summary": summary_total,
            "entity": entity_total,
            "counterparty": counterparty_total,
            "document": document_total,
        },
        "q_blank_brought_lines": q_blank_brought_lines,
    }


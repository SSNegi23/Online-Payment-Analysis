import os
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv(dotenv_path="../docker/.env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB"),
    "user":     os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def setup_table():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id                   SERIAL PRIMARY KEY,
            transaction_date     DATE,
            transaction_time     TIME,
            transaction_datetime TIMESTAMP,
            transaction_type     VARCHAR(10),
            paid_to              TEXT,
            paid_by              TEXT,
            amount               NUMERIC(12, 2),
            upi_transaction_id   VARCHAR(100),
            provider             VARCHAR(20),
            upi_id               TEXT,
            tag                  TEXT,
            note                 TEXT,
            created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (upi_transaction_id, provider)
        );
        CREATE INDEX IF NOT EXISTS idx_txn_date     ON transactions(transaction_date);
        CREATE INDEX IF NOT EXISTS idx_txn_provider ON transactions(provider);
        CREATE INDEX IF NOT EXISTS idx_txn_type     ON transactions(transaction_type);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Table ready.")

def insert_transactions(transactions):
    conn = get_connection()
    cur  = conn.cursor()
    sql = """
        INSERT INTO transactions
            (transaction_date, transaction_time, transaction_datetime,
             transaction_type, paid_to, paid_by, amount,
             upi_transaction_id, provider, upi_id, tag, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (upi_transaction_id, provider) DO NOTHING;
    """
    cur.execute("SELECT COUNT(*) FROM transactions;")
    before = cur.fetchone()[0]
    execute_batch(cur, sql, [t.to_tuple() for t in transactions], page_size=100)
    cur.execute("SELECT COUNT(*) FROM transactions;")
    after = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return after - before

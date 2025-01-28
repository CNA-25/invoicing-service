from fastapi import FastAPI, Request
import os
import psycopg
from psycopg.rows import dict_row

app = FastAPI()

DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_NAME = os.getenv("db_name")
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")

conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


@app.get("/")
def read_root():
    return { "Hello": "Rahti2", "v": "0.4" }


@app.get("/shipments")
def read_shipments():
    with psycopg.connect(conn_str, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM shipments")
            return cur.fetchall()
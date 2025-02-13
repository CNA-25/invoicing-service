from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os
import psycopg
from psycopg.rows import dict_row
from typing import List

app = FastAPI()

DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_NAME = os.getenv("db_name")
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")

conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class OrderItem(BaseModel):
    order_item_id: int
    product_id: int
    amount: int
    product_price: float
    product_name: str

class Order(BaseModel):
    user_id: int
    timestamp: str
    order_price: float
    order_id: int
    order_items: List[OrderItem]


@app.get("/")
def read_root():
    return { "Hello": "Rahti2", "v": "0.4" }


@app.get("/orders")
def read_orders():
    try:
        with psycopg.connect(conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        o.invoice_id, 
                        o.user_id, 
                        o.timestamp, 
                        o.order_price,
                        COALESCE(jsonb_agg(
                            jsonb_build_object(
                                'order_item_id', oi.order_item_id,
                                'product_id', oi.product_id,
                                'amount', oi.amount,
                                'product_price', oi.product_price,
                                'product_name', oi.product_name,
                                'total_price', oi.total_price
                            )
                        ) FILTER (WHERE oi.order_item_id IS NOT NULL), '[]'::jsonb) AS order_items
                    FROM orders o
                    LEFT JOIN order_items oi ON o.invoice_id = oi.invoice_id
                    GROUP BY o.invoice_id
                """)
                return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/orders")
def create_order(order: Order):
    try:
        with psycopg.connect(conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO orders (user_id, timestamp, order_price, order_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING invoice_id
                """, (order.user_id, order.timestamp, order.order_price, order.order_id))
                
                invoice_id = cur.fetchone()["invoice_id"]

                for item in order.order_items:
                    cur.execute("""
                        INSERT INTO order_items (order_item_id, product_id, amount, product_price, product_name, invoice_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (item.order_item_id, item.product_id, item.amount, item.product_price, item.product_name, invoice_id))
                
                conn.commit()

                return {"message": "Order created successfully", "invoice_id": invoice_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
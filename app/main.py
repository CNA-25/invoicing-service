from fastapi import FastAPI, Request, HTTPException
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


@app.get("/orders")
def read_orders():
    with psycopg.connect(conn_str, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.invoice_id, o.user_id, o.timestamp, o.order_price,
                    jsonb_agg(jsonb_build_object(
                        'order_item_id', oi.order_item_id,
                        'product_id', oi.product_id,
                        'amount', oi.amount,
                        'product_price', oi.product_price,
                        'product_name', oi.product_name,
                        'total_price', oi.total_price,
                        'invoice_id', oi.invoice_id,
                    )) AS order_items
                FROM orders o
                LEFT JOIN order_items oi ON o.invoice_id = oi.invoice_id
                GROUP BY o.invoice_id
            """)
            return cur.fetchall()
        
@app.post("/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
        order_id = data.get("order_id")
        user_id = data.get("user_id")
        timestamp = data.get("timestamp")
        order_price = data.get("order_price")
        order_items = data.get("order_items", [])

        if not all([order_id, user_id, timestamp, order_price, order_items]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (order,id, user_id, timestamp, order_price)
                    VALUES (%s, %s, %s, %s) RETURNING invoice_id
                    """,
                    (order_id, user_id, timestamp, order_price)
                )
                invoice_id = cur.fetchone()["invoice_id"]

                for item in order_items:
                    cur.execute(
                        """
                        INSERT INTO order_items (order_item_id, invoice_id, product_id, amount, product_price, product_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (item["order_item_id"], invoice_id, item["product_id"], item["amount"], item["product_price"], item["product_name"])
                    )

                conn.commit()

        return {"message": "Order created successfully", "invoice_id": invoice_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
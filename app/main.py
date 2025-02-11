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
                SELECT o.order_id, o.user_id, o.timestamp, o.order_price,
                    jsonb_agg(jsonb_build_object(
                        'order_item_id', oi.order_item_id,
                        'product_id', oi.product_id,
                        'amount', oi.amount,
                        'product_price', oi.product_price,
                        'product_name', oi.product_name,
                        'total_price', oi.total_price
                    )) AS order_items
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                GROUP BY o.order_id
            """)
            return cur.fetchall()
        
@app.post("/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
        user_id = data.get("userId")
        timestamp = data.get("timestamp")
        order_price = data.get("orderPrice")
        order_items = data.get("orderItems", [])

        if not all([user_id, timestamp, order_price, order_items]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (user_id, timestamp, order_price)
                    VALUES (%s, %s, %s) RETURNING order_id
                    """,
                    (user_id, timestamp, order_price)
                )
                order_id = cur.fetchone()["order_id"]

                for item in order_items:
                    cur.execute(
                        """
                        INSERT INTO order_items (order_id, product_id, amount, product_price, product_name)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (order_id, item["product_id"], item["amount"], item["product_price"], item["product_name"])
                    )

                conn.commit()

        return {"message": "Order created successfully", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
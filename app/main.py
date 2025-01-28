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


@app.get("/shipments")
def read_shipments():
    with psycopg.connect(conn_str, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM shipments")
            return cur.fetchall()
        
@app.post("/shipments")
async def create_shipments(request: Request):
    try:
        data = await request.json()
        shipment_id = data.get("shipment_id")
        user_id = data.get("user_id")
        timestamp = data.get("timestamp")
        order_price = data.get("order_price")
        order_id = data.get("order_id")
        order_item_id = data.get("order_item_id")
        product_id = data.get("product_id")
        amount = data.get("amount")
        product_price = data.get("product_price")
        product_name = data.get("product_name")

        if not all([shipment_id, user_id, timestamp, order_price, order_id, order_item_id, product_id, amount, product_price, product_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO shipments (
                            shipment_id, user_id, timestamp, order_price, order_id,
                            order_item_id, product_id, amount, product_price, product_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            shipment_id,
                            user_id,
                            timestamp,
                            order_price,
                            order_id,
                            order_item_id,
                            product_id,
                            amount,
                            product_price,
                            product_name,
                        ),
                    )
                    conn.commit()

                return {"message": "Shipment created successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
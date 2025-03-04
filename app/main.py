from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
import os
import psycopg
from psycopg.rows import dict_row
from typing import List
from weasyprint import HTML
import io
from fastapi.responses import StreamingResponse
import datetime
from app.middleware import verify_token
import requests
import base64

app = FastAPI()

DB_HOST = os.getenv("db_host")
DB_PORT = os.getenv("db_port")
DB_NAME = os.getenv("db_name")
DB_USER = os.getenv("db_user")
DB_PASSWORD = os.getenv("db_password")
EMAIL_URL = os.getenv("email_url")
INVOICE_URL = os.getenv("invoice_url")
USER_URL = os.getenv("user_url")
USER_MAIL = os.getenv("user_mail")
USER_PASS = os.getenv("user_pass")
USER_JWT = None

conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@app.on_event("startup")
def on_startup():
    login_user()

def login_user():
    global USER_JWT
    try:
        resp = requests.post(
            f"{USER_URL}/login",
            json={"email": USER_MAIL, "password": USER_PASS},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        USER_JWT = f"Bearer {data['access_token']}"
        print("Login success")
    except requests.RequestException as exc:
        print(f"Login failed: {exc}")
        USER_JWT = None

def fetch_user(user_id: int):
    global USER_JWT
    if not USER_JWT:
        login_user()
    headers = {"Authorization": USER_JWT}
    resp = requests.get(f"{USER_URL}/users/{user_id}", headers=headers)
    if resp.status_code == 401:
        login_user()
        headers["Authorization"] = USER_JWT
        resp = requests.get(f"{USER_URL}/users/{user_id}", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get("user_data") 

class OrderItem(BaseModel):
    order_item_id: int
    product_id: str
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

def send_invoice_pdf(invoice_id, order):
    invoice_pdf_bytes = generate_invoice_pdf(invoice_id)
    pdf_base64 = base64.b64encode(invoice_pdf_bytes).decode("utf-8")
    user_data = fetch_user(order.user_id)
    user_email = user_data.get("email", "test@mail.com")

    email_payload = {
        "to": user_email,
        "subject": f"Beercraft invoice #{invoice_id}",
        "body": f"Hi {user_data.get('name', 'customer')}, thanks for your purchase from Beercraft.",
        "pdfBase64": f"data:application/pdf;base64,{pdf_base64}"
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(f"{EMAIL_URL}/invoicing", json=email_payload, headers=headers, timeout=5)
    resp.raise_for_status()

def generate_invoice_pdf(invoice_id: int) -> bytes:
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        o.invoice_id, 
                        o.user_id, 
                        o.timestamp, 
                        o.order_price
                    FROM orders o
                    WHERE o.invoice_id = %s
                """, (invoice_id,))
                invoice_row = cur.fetchone()
                if not invoice_row:
                    raise HTTPException(status_code=404, detail="Invoice not found")
                
                (invoice_id_db, user_id_db, timestamp_db, order_price_db) = invoice_row

                cur.execute("""
                    SELECT product_id, amount, product_price, product_name, total_price
                    FROM order_items
                    WHERE invoice_id = %s
                """, (invoice_id,))
                order_items = cur.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    raw_timestamp = str(timestamp_db)
    parsed_timestamp = datetime.datetime.fromisoformat(raw_timestamp)
    formatted_timestamp = parsed_timestamp.strftime("%Y-%m-%d %H:%M")
    
    user_data = fetch_user(user_id_db)
    invoice_user_name = user_data["name"]
    invoice_user_email = user_data["email"]
    #address = user_data.get("address", {})
    #invoice_user_street = address.get("street", "N/A")
    #invoice_user_zipcode = address.get("zipcode", "N/A")
    #invoice_user_city = address.get("city", "N/A")
    #invoice_user_country = address.get("country", "N/A")

    html_content = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Invoice #{invoice_id_db}</title>
        <style>
          .invoice-box {{
            max-width: 800px;
            margin: auto;
            padding: 30px;
            border: 1px solid #eee;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
            font-size: 16px;
            line-height: 24px;
            font-family: 'Helvetica Neue', 'Helvetica', Arial, sans-serif;
            color: #555;
          }}
          .invoice-box table {{
            width: 100%;
            line-height: inherit;
            text-align: left;
          }}
          .invoice-box table td {{
            padding: 5px;
            vertical-align: top;
          }}
          .invoice-box table tr td:nth-child(2) {{
            text-align: right;
          }}
          .invoice-box table tr.top table td {{
            padding-bottom: 20px;
          }}
          .invoice-box table tr.top table td.title {{
            font-size: 45px;
            line-height: 45px;
            color: #333;
          }}
          .invoice-box table tr.information table td {{
            padding-bottom: 40px;
          }}
          .invoice-box table tr.heading td {{
            background: #eee;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
          }}
          .invoice-box table tr.item td {{
            border-bottom: 1px solid #eee;
          }}
          .invoice-box table tr.item.last td {{
            border-bottom: none;
          }}
          .invoice-box table tr.total td:nth-child(2) {{
            border-top: 2px solid #eee;
            font-weight: bold;
          }}
        </style>
      </head>
      <body>
        <div class="invoice-box">
          <table cellpadding="0" cellspacing="0">
            <tr class="top">
              <td colspan="2">
                <table>
                  <tr>
                    <td class="title">
                      <h1 style="margin: 0; font-size: 45px; line-height: 45px;">Beercraft</h1>
                    </td>
                    <td>
                      Invoice #: {invoice_id_db}<br />
                      {formatted_timestamp}<br />
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr class="information">
              <td colspan="2">
                <table>
                  <tr>
                    <td>
                      Beercraft<br />
                      Address
                    </td>
                    <td>
                      {invoice_user_name}<br />
                      {invoice_user_email}<br />
                      {{SHIPPING_ADDRESS}}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr class="heading">
              <td>Item</td>
              <td>Price</td>
            </tr>
    """

    for item in order_items:
        product_id, amount, product_price, product_name, total_price = item
        row_class = "item"
        html_content += f"""
            <tr class="{row_class}">
              <td>{amount} x {product_name} (ID: {product_id})</td>
              <td>{total_price:.2f}</td>
            </tr>
        """

    html_content += f"""
            <tr class="total">
              <td></td>
              <td>Total: {order_price_db:.2f}</td>
            </tr>
          </table>
        </div>
      </body>
    </html>
    """
    pdf_bytes = HTML(string=html_content).write_pdf()

    return pdf_bytes

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
        
@app.post("/orders", dependencies=[Depends(verify_token)])
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
                        INSERT INTO order_items (order_item_id, product_id, amount, product_price, product_name, total_price, invoice_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (item.order_item_id, item.product_id, item.amount, item.product_price, item.product_name, item.product_price * item.amount, invoice_id))
                
                conn.commit()

                send_invoice_pdf(invoice_id, order)

                return {"message": "Order created successfully", "invoice_id": invoice_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
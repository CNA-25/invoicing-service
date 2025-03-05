# invoicing-service

## Databas /orders

### Orders table:
- order_id - INTEGER
- user_id - INTEGER
- timestamp - TIMESTAMP (without time zone)
- order_price - NUMERIC
- shipping_address - TEXT

### Order_items table:
- order_item_id - INTEGER
- order_id - INTEGER
- product_id - VARCHAR
- amount - INTEGER
- product_price - NUMERIC
- product_name - TEXT
- total_price - NUMERIC

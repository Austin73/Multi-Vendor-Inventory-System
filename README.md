# Multi-Vendor Inventory System

A FastAPI backend service for managing product inventory with many-to-many vendor relationships and a flexible purchase order flow.

---

## Features

- **Stock Management** — CRUD for inventory items with SKU-based uniqueness and quantity tracking
- **Vendor Management** — Vendor registry with status lifecycle (active / inactive / suspended)
- **Many-to-Many Association** — Link any stock item to multiple approved vendors, each with their own pricing and lead time
- **Purchase Orders** — Create POs against a specific vendor; enforces that the vendor is approved for every requested item; price pulled automatically from the link
- **Order Lifecycle** — State-machine transitions: `draft → submitted → confirmed → received` (with cancellation available at each step)

---

## Tech Stack

| Layer      | Technology                      |
| ---------- | ------------------------------- |
| Framework  | FastAPI                         |
| ORM        | SQLAlchemy 2.0 (async)          |
| Database   | PostgreSQL 16                   |
| Migrations | Alembic                         |
| Validation | Pydantic v2                     |
| Tests      | pytest + pytest-asyncio + httpx |

---

## Project Structure

```
inventory_system/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── stock_items.py
│   │   │   ├── vendors.py
│   │   │   └── purchase_orders.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   └── exceptions.py      # Custom domain exceptions
│   ├── db/
│   │   └── session.py         # Async engine + session factory
│   ├── models/
│   │   ├── base.py            # UUID PK + timestamp mixin
│   │   ├── enums.py
│   │   └── inventory.py       # All ORM models
│   ├── repositories/          # Data access layer
│   ├── schemas/               # Pydantic request/response models
│   ├── services/              # Business logic
│   └── main.py                # App factory
├── alembic/                   # Database migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Getting Started

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your database credentials if needed
```

The API will be available at `http://localhost:8000`.

### 2. Run locally

```bash
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Ensure PostgreSQL is running, then:
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Run migrations

```bash
alembic upgrade head

# To generate a new migration after model changes:
alembic revision --autogenerate -m "describe your change"
```

---

## API Reference

Interactive docs available at `http://localhost:8000/docs`

### Stock Items

| Method   | Endpoint                                 | Description               |
| -------- | ---------------------------------------- | ------------------------- |
| `POST`   | `/api/v1/stock-items/`                   | Create a stock item       |
| `GET`    | `/api/v1/stock-items/`                   | List all items            |
| `GET`    | `/api/v1/stock-items/{id}`               | Get item with vendor list |
| `PATCH`  | `/api/v1/stock-items/{id}`               | Update item details       |
| `DELETE` | `/api/v1/stock-items/{id}`               | Delete item               |
| `POST`   | `/api/v1/stock-items/{id}/adjust-stock`  | Adjust quantity           |
| `GET`    | `/api/v1/stock-items/{id}/vendors`       | List approved vendors     |
| `POST`   | `/api/v1/stock-items/{id}/vendors`       | Link a vendor             |
| `PATCH`  | `/api/v1/stock-items/{id}/vendors/{vid}` | Update vendor link        |
| `DELETE` | `/api/v1/stock-items/{id}/vendors/{vid}` | Unlink a vendor           |

### Vendors

| Method   | Endpoint               | Description               |
| -------- | ---------------------- | ------------------------- |
| `POST`   | `/api/v1/vendors/`     | Register a vendor         |
| `GET`    | `/api/v1/vendors/`     | List all vendors          |
| `GET`    | `/api/v1/vendors/{id}` | Get vendor with item list |
| `PATCH`  | `/api/v1/vendors/{id}` | Update / change status    |
| `DELETE` | `/api/v1/vendors/{id}` | Delete vendor             |

### Purchase Orders

| Method  | Endpoint                              | Description                    |
| ------- | ------------------------------------- | ------------------------------ |
| `POST`  | `/api/v1/purchase-orders/`            | Create purchase order          |
| `GET`   | `/api/v1/purchase-orders/`            | List orders (filter by vendor) |
| `GET`   | `/api/v1/purchase-orders/{id}`        | Get full order details         |
| `PATCH` | `/api/v1/purchase-orders/{id}/status` | Advance order status           |
| `POST`  | `/api/v1/purchase-orders/{id}/cancel` | Cancel order                   |

---

## Example Workflow

```bash
# 1. Create a stock item
curl -X POST http://localhost:8000/api/v1/stock-items/ \
  -H "Content-Type: application/json" \
  -d '{"sku": "BOLT-M8", "name": "M8 Hex Bolt", "unit_price": "0.50"}'

# 2. Create a vendor
curl -X POST http://localhost:8000/api/v1/vendors/ \
  -H "Content-Type: application/json" \
  -d '{"name": "TechParts Ltd", "email": "orders@techparts.com"}'

# 3. Link the vendor to the stock item with agreed pricing
curl -X POST http://localhost:8000/api/v1/stock-items/{item_id}/vendors \
  -H "Content-Type: application/json" \
  -d '{"vendor_id": "{vendor_id}", "vendor_price": "0.42", "lead_time_days": 5}'

# 4. Create a purchase order — price is auto-filled from the link
curl -X POST http://localhost:8000/api/v1/purchase-orders/ \
  -H "Content-Type: application/json" \
  -d '{"vendor_id": "{vendor_id}", "lines": [{"stock_item_id": "{item_id}", "quantity": 500}]}'
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx aiosqlite
pytest -v
```

Tests use an in-memory SQLite database so no external services are needed.

---

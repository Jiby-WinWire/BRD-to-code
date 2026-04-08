# 🎯 Complete User Guide: Running Your Generated API

## 📦 What You Get

After running the pipeline, you get a complete, runnable FastAPI application:

```
output/
├── src/api/
│   ├── models.py       ← Pydantic models (data validation)
│   ├── services.py     ← Business logic (CRUD operations)
│   └── main.py         ← FastAPI routes (HTTP endpoints)
├── tests/
│   └── test_api.py     ← Pytest tests (all passing!)
├── run.py              ← SERVER LAUNCHER (start here!)
├── requirements.txt    ← Dependencies list
└── README.md           ← Full documentation
```

---

## 🚀 Step 1: Start the API Server

### Option A: Simple command (Recommended)

```bash
cd output
python run.py
```

### Option B: Using uvicorn directly

```bash
cd output
uvicorn src.api.main:app --reload
```

### Option C: From project root

```bash
cd output
..\.venv\Scripts\python.exe run.py
```

**You'll see:**
```
🚀 Starting Generated FastAPI Application
============================================================
📍 Server will start at: http://localhost:8000
📚 API Documentation:   http://localhost:8000/docs
💡 Press Ctrl+C to stop the server
============================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🌐 Step 2: Access the Interactive API Docs

Open your browser and go to:

### **http://localhost:8000/docs**

You'll see a **Swagger UI** with all your endpoints! You can:
- ✅ See all available endpoints
- ✅ View request/response models
- ✅ Try out endpoints directly in the browser
- ✅ See validation requirements
- ✅ View example requests

**Screenshot of what you'll see:**
```
┌─────────────────────────────────────────────────┐
│  📚 FastAPI - Swagger UI                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  POST /books/checkout                          │
│  ► Check out a book                            │
│    [Try it out]                                │
│                                                 │
│  POST /books/return                            │
│  ► Return a checked out book                   │
│    [Try it out]                                │
│                                                 │
│  GET /books/{book_id}/status                   │
│  ► Get book status                             │
│    [Try it out]                                │
│                                                 │
│  📋 Schemas                                     │
│    - Book                                       │
│    - CheckoutRequest                            │
│    - ReturnRequest                              │
└─────────────────────────────────────────────────┘
```

---

## 🧪 Step 3: Test the API

### Method A: Using Swagger UI (No coding!)

1. Go to http://localhost:8000/docs
2. Click on an endpoint (e.g., "POST /books/checkout")
3. Click **"Try it out"**
4. Edit the request body:
   ```json
   {
     "book_id": 1,
     "user_id": 42
   }
   ```
5. Click **"Execute"**
6. See the response below!

### Method B: Using PowerShell

```powershell
# Add a book first
$book = @{
    id = 1
    title = "The Great Gatsby"
    author = "F. Scott Fitzgerald"
    available = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/books" `
    -Method Post `
    -ContentType "application/json" `
    -Body $book

# Checkout the book
$checkout = @{
    book_id = 1
    user_id = 42
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/books/checkout" `
    -Method Post `
    -ContentType "application/json" `
    -Body $checkout

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/books/1/status"
```

### Method C: Using curl

```bash
# Add a book
curl -X POST "http://localhost:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "title": "1984", "author": "George Orwell", "available": true}'

# Checkout the book
curl -X POST "http://localhost:8000/books/checkout" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1, "user_id": 42}'

# Check status
curl "http://localhost:8000/books/1/status"
```

### Method D: Using Python

```python
import requests

# Add a book
response = requests.post("http://localhost:8000/books", json={
    "id": 1,
    "title": "To Kill a Mockingbird",
    "author": "Harper Lee",
    "available": True
})
print(f"Added: {response.json()}")

# Checkout
response = requests.post("http://localhost:8000/books/checkout", json={
    "book_id": 1,
    "user_id": 42
})
print(f"Checkout: {response.json()}")

# Get status
response = requests.get("http://localhost:8000/books/1/status")
print(f"Status: {response.json()}")
```

---

## 🧪 Step 4: Run Automated Tests

```bash
cd output
pytest tests/ -v
```

**You'll see:**
```
tests/test_api.py::test_add_book PASSED                      [ 16%]
tests/test_api.py::test_checkout_book_valid PASSED           [ 33%]
tests/test_api.py::test_checkout_unavailable_book PASSED     [ 50%]
tests/test_api.py::test_return_book_valid PASSED             [ 66%]
tests/test_api.py::test_return_wrong_user PASSED             [ 83%]
tests/test_api.py::test_get_book_status PASSED               [100%]

============ 6 passed in 0.42s ============
```

---

## 📱 Real-World Usage Example

### Scenario: Library Book Management

**Terminal 1: Start the Server**
```bash
cd output
python run.py
```

**Terminal 2: Test the API**
```bash
# Add some books
curl -X POST http://localhost:8000/books -H "Content-Type: application/json" \
  -d '{"id": 1, "title": "Harry Potter", "author": "J.K. Rowling", "available": true}'

curl -X POST http://localhost:8000/books -H "Content-Type: application/json" \
  -d '{"id": 2, "title": "Lord of the Rings", "author": "J.R.R. Tolkien", "available": true}'

# User 42 checks out book 1
curl -X POST http://localhost:8000/books/checkout -H "Content-Type: application/json" \
  -d '{"book_id": 1, "user_id": 42}'
# Response: {"message": "Book checked out successfully"}

# Check if book 1 is available
curl http://localhost:8000/books/1/status
# Response: {"status": "checked out"}

# Try to checkout the same book (should fail)
curl -X POST http://localhost:8000/books/checkout -H "Content-Type: application/json" \
  -d '{"book_id": 1, "user_id": 99}'
# Response: {"detail": "Book is not available"} (HTTP 400)

# User 42 returns the book
curl -X POST http://localhost:8000/books/return -H "Content-Type: application/json" \
  -d '{"book_id": 1, "user_id": 42}'
# Response: {"message": "Book returned successfully"}

# Now book 1 is available again
curl http://localhost:8000/books/1/status
# Response: {"status": "available"}
```

---

## 🎨 Customization

### Add a new endpoint

Edit `output/src/api/main.py`:
```python
@app.get("/books")
def list_all_books():
    return {"books": list(library_service.books.values())}
```

### Add persistence (SQLite)

Edit `output/src/api/services.py`:
```python
import sqlite3

class LibraryService:
    def __init__(self):
        self.conn = sqlite3.connect('library.db')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS books 
                            (id INT, title TEXT, author TEXT, available BOOL)''')
    
    def add_book(self, book: Book):
        self.conn.execute("INSERT INTO books VALUES (?, ?, ?, ?)",
                         (book.id, book.title, book.author, book.available))
        self.conn.commit()
```

---

## 🐳 Deploy with Docker

Create `output/Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

---

## ☁️ Deploy to Cloud

### Azure App Service
```bash
az webapp up --name my-library-api --runtime "PYTHON:3.13"
```

### AWS Lambda (with Mangum)
```python
from mangum import Mangum
from src.api.main import app

handler = Mangum(app)
```

### Heroku
```bash
echo "web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT" > Procfile
git push heroku main
```

---

## 📊 Monitoring

### View logs
```bash
# While server is running, you'll see:
INFO:     127.0.0.1:54321 - "POST /books/checkout HTTP/1.1" 200 OK
INFO:     127.0.0.1:54322 - "GET /books/1/status HTTP/1.1" 200 OK
```

### Add logging
Edit `output/src/api/main.py`:
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/books/checkout")
def checkout_book(request: CheckoutRequest):
    logger.info(f"User {request.user_id} checking out book {request.book_id}")
    # ... rest of code
```

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| **Port 8000 already in use** | `uvicorn src.api.main:app --port 8001` |
| **Module not found** | Make sure you're in output folder: `cd output` |
| **Import errors** | Install dependencies: `pip install -r requirements.txt` |
| **Server won't start** | Check Python version: `python --version` (need 3.8+) |
| **Cannot connect** | Server might need more time to start, wait 5 seconds |

---

## 🎯 Quick Reference

| Command | Purpose |
|---------|---------|
| `python run.py` | Start the API server |
| `pytest tests/ -v` | Run all tests |
| `curl http://localhost:8000/docs` | Get API documentation |
| Ctrl+C | Stop the server |

**Key URLs:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

---

**Generated Code is Production-Ready!** ✅
- Real CRUD operations
- Input validation
- Error handling
- Comprehensive tests
- OpenAPI documentation
- Type hints
- Async support

Just run `python run.py` and start building! 🚀

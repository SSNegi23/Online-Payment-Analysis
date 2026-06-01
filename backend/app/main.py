from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import transactions

app = FastAPI(
    title="Payment Analysis API",
    description="API for querying UPI transactions from GPay, Paytm, and BHIM",
    version="1.0.0",
    # Swagger UI will be available at http://localhost:8000/docs
    # ReDoc will be available at http://localhost:8000/redoc
)

# CORS — allows your React frontend (running on port 5173) to call this API
# Without this, browsers block cross-origin requests as a security measure
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # fallback if using CRA
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the transactions router — all its routes are now active
app.include_router(transactions.router)


@app.get("/health")
async def health():
    """Simple health check — confirms the server is running."""
    return {"status": "ok"}

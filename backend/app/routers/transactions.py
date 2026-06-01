from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional
from datetime import date
import math

from ..database import get_db
from ..models import Transaction
from ..schemas import TransactionOut, PaginatedTransactions, TransactionSummary

router = APIRouter(
    prefix="/transactions",   # all routes here start with /transactions
    tags=["Transactions"],    # groups them together in Swagger UI
)


@router.get("", response_model=PaginatedTransactions)
async def get_transactions(
    # --- Pagination ---
    page:     int = Query(default=1,  ge=1,    description="Page number"),
    limit:    int = Query(default=20, ge=1, le=100, description="Rows per page"),

    # --- Filters ---
    provider: Optional[str]  = Query(default=None, description="gpay | paytm | bhim"),
    type:     Optional[str]  = Query(default=None, description="Paid | Received"),
    search:   Optional[str]  = Query(default=None, description="Search paid_to or paid_by"),
    date_from:Optional[date] = Query(default=None, description="Start date YYYY-MM-DD"),
    date_to:  Optional[date] = Query(default=None, description="End date YYYY-MM-DD"),

    # --- Sorting ---
    sort_by:  str  = Query(default="transaction_datetime", description="Column to sort by"),
    order:    str  = Query(default="desc", description="asc | desc"),

    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated, filterable, sortable list of transactions.

    How pagination works:
      page=1, limit=20 → rows 1-20
      page=2, limit=20 → rows 21-40
      offset = (page - 1) * limit
    """

    # Start with a base query — we'll chain filters onto it
    query = select(Transaction)

    # Build filter conditions list — only add a filter if the param was provided
    filters = []

    if provider:
        filters.append(Transaction.provider == provider.lower())

    if type:
        filters.append(Transaction.transaction_type == type)

    if search:
        # ilike = case-insensitive LIKE — searches both paid_to and paid_by
        term = f"%{search}%"
        filters.append(
            or_(
                Transaction.paid_to.ilike(term),
                Transaction.paid_by.ilike(term),
            )
        )

    if date_from:
        filters.append(Transaction.transaction_date >= date_from)

    if date_to:
        filters.append(Transaction.transaction_date <= date_to)

    # Apply all filters at once with AND logic
    if filters:
        query = query.where(and_(*filters))

    # Count total matching rows BEFORE applying pagination
    # We need this to calculate total_pages
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply sorting
    # getattr lets us dynamically access Transaction.amount, Transaction.transaction_date etc.
    sort_column = getattr(Transaction, sort_by, Transaction.transaction_datetime)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination — offset skips rows, limit caps how many we return
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    # Execute the final query
    result = await db.execute(query)
    transactions = result.scalars().all()

    return PaginatedTransactions(
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit) if total > 0 else 1,
        data=transactions,
    )


@router.get("/summary", response_model=TransactionSummary)
async def get_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns high-level stats for the dashboard header:
    total paid, total received, transaction count, active providers.
    """
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(Transaction.amount).filter(Transaction.transaction_type == "Paid"),
                0
            ).label("total_paid"),
            func.coalesce(
                func.sum(Transaction.amount).filter(Transaction.transaction_type == "Received"),
                0
            ).label("total_received"),
            func.count(Transaction.id).label("transaction_count"),
        )
    )
    row = result.one()

    # Get distinct providers
    providers_result = await db.execute(
        select(Transaction.provider).distinct().where(Transaction.provider.isnot(None))
    )
    providers = [p for (p,) in providers_result.all()]

    return TransactionSummary(
        total_paid=row.total_paid,
        total_received=row.total_received,
        transaction_count=row.transaction_count,
        providers=providers,
    )


@router.get("/providers", response_model=list[str])
async def get_providers(db: AsyncSession = Depends(get_db)):
    """Returns list of distinct providers currently in the DB."""
    result = await db.execute(
        select(Transaction.provider).distinct().where(Transaction.provider.isnot(None))
    )
    return [p for (p,) in result.all()]


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    """Returns a single transaction by its DB id."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn

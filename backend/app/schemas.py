from pydantic import BaseModel, ConfigDict
from datetime import date, time, datetime
from typing import Optional
from decimal import Decimal


class TransactionOut(BaseModel):
    """
    What the API returns for a single transaction.
    Pydantic validates and serialises the SQLAlchemy model into this shape.
    'Out' suffix is a convention meaning 'outgoing / response'.
    """
    id:                   int
    transaction_date:     Optional[date]
    transaction_time:     Optional[time]
    transaction_datetime: Optional[datetime]
    transaction_type:     Optional[str]
    paid_to:              Optional[str]
    paid_by:              Optional[str]
    amount:               Optional[Decimal]
    upi_transaction_id:   Optional[str]
    provider:             Optional[str]
    upi_id:               Optional[str]
    tag:                  Optional[str]
    note:                 Optional[str]
    created_at:           Optional[datetime]

    # This tells Pydantic to read data from SQLAlchemy model attributes
    # instead of expecting a plain dict — required for ORM integration
    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactions(BaseModel):
    """Wraps a list of transactions with pagination metadata."""
    total:        int           # total rows matching the filters
    page:         int           # current page number
    limit:        int           # rows per page
    total_pages:  int           # total number of pages
    data:         list[TransactionOut]


class TransactionSummary(BaseModel):
    """High-level stats shown at the top of the dashboard."""
    total_paid:         Decimal
    total_received:     Decimal
    transaction_count:  int
    providers:          list[str]   # e.g. ['gpay', 'paytm', 'bhim']

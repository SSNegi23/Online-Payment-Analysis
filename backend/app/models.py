from sqlalchemy import Column, Integer, String, Numeric, Date, Time, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class Transaction(Base):
    """
    SQLAlchemy model for the 'transactions' table.
    This mirrors the table your ETL already created — we are NOT
    creating a new table, just telling SQLAlchemy its shape so it
    can build queries against it.
    """
    __tablename__ = "transactions"

    id                   = Column(Integer, primary_key=True, index=True)
    transaction_date     = Column(Date)
    transaction_time     = Column(Time)
    transaction_datetime = Column(DateTime)
    transaction_type     = Column(String(10))   # 'Paid' or 'Received'
    paid_to              = Column(Text)
    paid_by              = Column(Text)
    amount               = Column(Numeric(12, 2))
    upi_transaction_id   = Column(String(100))
    provider             = Column(String(20))   # 'gpay' | 'paytm' | 'bhim'
    upi_id               = Column(Text)
    tag                  = Column(Text)
    note                 = Column(Text)
    created_at           = Column(DateTime, server_default=func.now())

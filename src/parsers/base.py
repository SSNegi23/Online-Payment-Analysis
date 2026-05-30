from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Optional


@dataclass
class Transaction:
    """
    Normalised transaction — same shape regardless of provider.
    Every parser must produce a list of these.
    """
    transaction_date:     date
    transaction_time:     Optional[time]
    transaction_datetime: Optional[datetime]
    transaction_type:     str             # 'Paid' | 'Received'
    paid_to:              str
    paid_by:              str
    amount:               float
    upi_transaction_id:   str
    provider:             str             # 'gpay' | 'paytm' | ...
    upi_id:               Optional[str] = None   # counterparty UPI handle
    tag:                  Optional[str] = None   # Paytm tag  e.g. "Food"
    note:                 Optional[str] = None   # Paytm note

    def to_tuple(self):
        """Returns values in the exact order expected by db.insert_transactions."""
        return (
            self.transaction_date,
            self.transaction_time,
            self.transaction_datetime,
            self.transaction_type,
            self.paid_to,
            self.paid_by,
            self.amount,
            self.upi_transaction_id,
            self.provider,
            self.upi_id,
            self.tag,
            self.note,
        )


class BaseParser(ABC):
    """All provider parsers must implement this interface."""

    @abstractmethod
    def extract_from_pdf(self, pdf_path: str) -> list[Transaction]:
        """Open pdf_path, parse every page, return list of Transaction objects."""
        pass

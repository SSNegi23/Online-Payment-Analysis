from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    provider:             str             # 'gpay' | 'paytm' | 'bhim'
    upi_id:               Optional[str] = None
    tag:                  Optional[str] = None
    note:                 Optional[str] = None

    def to_tuple(self):
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

    def deduplicate(self, transactions: list) -> list:
        """
        Remove transactions with duplicate UPI IDs within the same batch.
        This is a safety net — the DB also deduplicates via ON CONFLICT,
        but catching it here keeps logs accurate and reduces DB round-trips.
        """
        seen = set()
        unique = []
        for txn in transactions:
            if txn.upi_transaction_id not in seen:
                seen.add(txn.upi_transaction_id)
                unique.append(txn)
        skipped = len(transactions) - len(unique)
        if skipped:
            print(f"  [{self.__class__.__name__}] Skipped {skipped} duplicate(s)")
        return unique

    @abstractmethod
    def extract_from_pdf(self, file_path: str) -> list:
        """Open file_path, parse every transaction, return list of Transaction objects."""
        pass

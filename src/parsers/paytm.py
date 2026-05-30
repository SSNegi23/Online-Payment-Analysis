import re
import pdfplumber
from datetime import datetime
from .base import BaseParser, Transaction

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}


class PaytmParser(BaseParser):
    """
    Parses Paytm UPI transaction statement PDFs.

    PDF quirk: unlike GPay, spaces ARE preserved. Each transaction spans
    multiple lines. The date and action are on the SAME line, time on the next.

    Line structure per transaction:
      Line 1: "25 May Paid to Zepto           Tag: State Bank  - Rs.189"
      Line 2: "9:06 PM"
      Line 3: "UPI ID: zeptoonline@ybl on     # Groceries  Of India - 34"
      Line 4: "UPI Ref No: 206961293214"

    Dates have NO year — year is inferred from the statement period header.
    """

    # Matches the main transaction line
    TXN_LINE = re.compile(
        r'^(\d{1,2})\s+'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+'
        r'(Paid to|Received from|Money sent to)\s+'
        r'(.+?)\s+'
        r'(?:Tag:|Note:).+?\s+'
        r'([+-]\s*Rs\.[\d,]+(?:\.\d+)?)$'
    )
    TIME_LINE    = re.compile(r'^(\d{1,2}:\d{2}\s*[AP]M)$')
    UPI_ID_LINE  = re.compile(r'^UPI ID:\s*(\S+?)(?:\s+on\s*)?(?:\s+#.*)?(?:\s+Of\s+India.*)?$')
    UPI_REF_LINE = re.compile(r'^UPI Ref No:\s*(\d+)')

    def _extract_date_range(self, full_text: str):
        """
        Extracts start and end date from header like "27 MAY'25 - 26 MAY'26".
        Used to resolve the year for each transaction date.
        """
        m = re.search(
            r"(\d+)\s+(\w+)'(\d{2})\s*-\s*(\d+)\s+(\w+)'(\d{2})",
            full_text
        )
        if m:
            d1, mo1, y1, d2, mo2, y2 = m.groups()
            start = datetime(
                int("20" + y1),
                int(MONTH_MAP[mo1.capitalize()[:3]]),
                int(d1)
            ).date()
            end = datetime(
                int("20" + y2),
                int(MONTH_MAP[mo2.capitalize()[:3]]),
                int(d2)
            ).date()
            return start, end
        today = datetime.now().date()
        return today, today

    def _resolve_year(self, day: str, month_str: str, start_date, end_date):
        """
        Paytm dates have no year. Try both boundary years and return
        the one that falls inside the statement date range.
        Fallback to end_year if neither fits cleanly.
        """
        mon = int(MONTH_MAP[month_str[:3].capitalize()])
        day = int(day)
        for year in [end_date.year, start_date.year]:
            try:
                d = datetime(year, mon, day).date()
                if start_date <= d <= end_date:
                    return d
            except ValueError:
                continue
        # Fallback
        try:
            return datetime(end_date.year, mon, day).date()
        except ValueError:
            return None

    def _parse_amount(self, s: str) -> float:
        """'- Rs.2,787.50' → 2787.50,  '+ Rs.1,500' → 1500.0"""
        m = re.search(r'Rs\.([\d,]+(?:\.\d+)?)', s)
        if m:
            return float(m.group(1).replace(',', ''))
        return 0.0

    def _parse_transactions(self, full_text: str, start_date, end_date) -> list[Transaction]:
        results = []
        lines = full_text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = self.TXN_LINE.match(line)

            if m:
                day, month_str, action, counterparty, amount_str = m.groups()
                counterparty = counterparty.strip()

                txn_date = self._resolve_year(day, month_str, start_date, end_date)
                txn_time = None
                upi_id = upi_ref = tag = note = ""

                # Scan ahead up to 10 lines for time, UPI ID, ref, tag, note
                j = i + 1
                while j < min(i + 10, len(lines)):
                    nl = lines[j].strip()

                    if self.TIME_LINE.match(nl) and not txn_time:
                        txn_time = datetime.strptime(nl.replace(" ", ""), "%I:%M%p").time()

                    elif nl.startswith("UPI ID:") and not upi_id:
                        um = self.UPI_ID_LINE.match(nl)
                        if um:
                            upi_id = um.group(1)

                    elif nl.startswith("UPI Ref No:") and not upi_ref:
                        rm = self.UPI_REF_LINE.match(nl)
                        if rm:
                            upi_ref = rm.group(1)

                    elif nl.startswith("# ") and not tag:
                        tag = nl[2:].strip()

                    elif nl.startswith("Note:") and not note:
                        note = nl[5:].strip()

                    # Stop if next transaction starts
                    elif self.TXN_LINE.match(nl):
                        break

                    j += 1

                amount   = self._parse_amount(amount_str)
                txn_type = "Received" if action == "Received from" else "Paid"
                paid_to  = counterparty if txn_type == "Paid"     else "State Bank Of India - 34"
                paid_by  = counterparty if txn_type == "Received" else "State Bank Of India - 34"
                txn_dt   = datetime.combine(txn_date, txn_time) if txn_date and txn_time else None

                results.append(Transaction(
                    transaction_date=txn_date,
                    transaction_time=txn_time,
                    transaction_datetime=txn_dt,
                    transaction_type=txn_type,
                    paid_to=paid_to,
                    paid_by=paid_by,
                    amount=amount,
                    upi_transaction_id=upi_ref or "",
                    provider="paytm",
                    upi_id=upi_id or None,
                    tag=tag or None,
                    note=note or None,
                ))

                i = j  # jump past the block we just consumed
                continue

            i += 1

        return results

    def extract_from_pdf(self, pdf_path: str) -> list[Transaction]:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for idx, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text += "\n" + text
                print(f"  [Paytm] Page {idx}/{total}", end="\r")

        print()
        start_date, end_date = self._extract_date_range(full_text)
        txns = self._parse_transactions(full_text, start_date, end_date)
        print(f"  [Paytm] {len(txns)} transactions extracted")
        return txns

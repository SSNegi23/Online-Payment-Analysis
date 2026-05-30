import re
import pdfplumber
from datetime import datetime
from .base import BaseParser, Transaction

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}


class GPayParser(BaseParser):
    """
    Parses Google Pay transaction statement PDFs.

    PDF quirk: pdfplumber strips all spaces, so text like
    "Paid to EatClub" becomes "PaidtoEatClub". Regexes account for this.

    Line structure per transaction (3 lines):
      Line 1: "01Nov,2025 PaidtoEatClub ₹220"
      Line 2: "01:31PM UPITransactionID:530529326695"
      Line 3: "PaidbyStateBankofIndia3134"
    """

    def _parse_date(self, s: str):
        m = re.match(r'(\d{2})(\w{3}),(\d{4})', s)
        if m:
            day, mon, year = m.groups()
            return datetime.strptime(f"{day}/{MONTH_MAP[mon]}/{year}", "%d/%m/%Y").date()
        return None

    def _parse_time(self, s: str):
        return datetime.strptime(s, "%I:%M%p").time()

    def _parse_amount(self, s: str) -> float:
        return float(s.replace("₹", "").replace(",", ""))

    def _parse_page(self, text: str) -> list[Transaction]:
        results = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        i = 0
        while i < len(lines):
            line = lines[i]

            # "01Nov,2025 PaidtoEatClub ₹220"
            m = re.match(
                r'^(\d{2}\w+,\d{4})\s+((?:Paid|Received)\S+?)\s+(₹[\d,]+(?:\.\d+)?)$',
                line
            )
            if m:
                date_str, raw_action, amount_str = m.groups()
                time_str = upi_id = bank = bank_dir = ""

                # Line 2: time + UPI ID
                if i + 1 < len(lines):
                    tm = re.match(
                        r'^(\d{1,2}:\d{2}[AP]M)\s+UPITransactionID:(\d+)$',
                        lines[i + 1]
                    )
                    if tm:
                        time_str, upi_id = tm.groups()
                        i += 1

                # Line 3: bank direction
                if i + 1 < len(lines):
                    bm = re.match(r'^(Paidby|Paidto)(.+)$', lines[i + 1])
                    if bm:
                        bank_dir, bank = bm.groups()
                        i += 1

                paid_m = re.match(r'^Paidto(.+)$', raw_action)
                recv_m = re.match(r'^Receivedfrom(.+)$', raw_action, re.IGNORECASE)

                if paid_m:
                    txn_type = "Paid"
                    paid_to  = paid_m.group(1)
                    paid_by  = bank if bank_dir == "Paidby" else ""
                elif recv_m:
                    txn_type = "Received"
                    paid_by  = recv_m.group(1)
                    paid_to  = bank if bank_dir == "Paidto" else ""
                else:
                    i += 1
                    continue

                txn_date = self._parse_date(date_str)
                txn_time = self._parse_time(time_str) if time_str else None
                txn_dt   = datetime.combine(txn_date, txn_time) if txn_date and txn_time else None

                results.append(Transaction(
                    transaction_date=txn_date,
                    transaction_time=txn_time,
                    transaction_datetime=txn_dt,
                    transaction_type=txn_type,
                    paid_to=paid_to,
                    paid_by=paid_by,
                    amount=self._parse_amount(amount_str),
                    upi_transaction_id=upi_id or "",
                    provider="gpay",
                ))

            i += 1
        return results

    def extract_from_pdf(self, pdf_path: str) -> list[Transaction]:
        all_txns = []
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for idx, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    all_txns.extend(self._parse_page(text))
                print(f"  [GPay] Page {idx}/{total} — {len(all_txns)} transactions", end="\r")
        print()
        return all_txns

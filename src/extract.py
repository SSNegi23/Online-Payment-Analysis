import re
from datetime import datetime

MONTH_MAP = {
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
}

def parse_date(date_str):
    match = re.match(r'(\d{2})(\w{3}),(\d{4})', date_str)
    if match:
        day, mon, year = match.groups()
        return datetime.strptime(f"{day}/{MONTH_MAP[mon]}/{year}", "%d/%m/%Y").date()
    return None

def parse_time(time_str):
    return datetime.strptime(time_str, "%I:%M%p").time()

def parse_amount(amount_str):
    return float(amount_str.replace("₹", "").replace(",", ""))

def parse_page(text):
    transactions = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        date_match = re.match(
            r'^(\d{2}\w+,\d{4})\s+((?:Paid|Received)\S+?)\s+(₹[\d,]+(?:\.\d+)?)$',
            line
        )
        if date_match:
            date_str, raw_action, amount_str = date_match.groups()
            time_str = upi_id = bank = bank_dir = ""

            if i + 1 < len(lines):
                m = re.match(r'^(\d{1,2}:\d{2}[AP]M)\s+UPITransactionID:(\d+)$', lines[i+1])
                if m:
                    time_str, upi_id = m.groups()
                    i += 1

            if i + 1 < len(lines):
                m = re.match(r'^(Paidby|Paidto)(.+)$', lines[i+1])
                if m:
                    bank_dir, bank = m.groups()
                    i += 1

            paid_m = re.match(r'^Paidto(.+)$', raw_action)
            recv_m = re.match(r'^Receivedfrom(.+)$', raw_action, re.IGNORECASE)

            if paid_m:
                txn_type, paid_to = "Paid", paid_m.group(1)
                paid_by = bank if bank_dir == "Paidby" else ""
            elif recv_m:
                txn_type, paid_by = "Received", recv_m.group(1)
                paid_to = bank if bank_dir == "Paidto" else ""
            else:
                i += 1
                continue

            txn_date = parse_date(date_str)
            txn_time = parse_time(time_str) if time_str else None
            txn_dt   = datetime.combine(txn_date, txn_time) if txn_date and txn_time else None

            transactions.append((
                txn_date, txn_time, txn_dt,
                txn_type, paid_to, paid_by,
                parse_amount(amount_str),
                upi_id or None
            ))
        i += 1
    return transactions

def extract_from_pdf(pdf_path):
    import pdfplumber
    all_txns = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for idx, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                all_txns.extend(parse_page(text))
            print(f"  Page {idx}/{total} — {len(all_txns)} transactions", end="\r")
    print()
    return all_txns


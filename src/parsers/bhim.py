import re
import xml.etree.ElementTree as ET
from datetime import datetime
from .base import BaseParser, Transaction


class BHIMParser(BaseParser):
    """
    Parses BHIM UPI transaction history HTML files.

    Structure: The HTML file contains a JavaScript variable:
        var DATA = '<UPITransactions ...>...</UPITransactions>';
    which is a signed XML document containing all transactions as attributes.

    Each <Transaction> element has:
        Id, Amount, BenefitType (DR=Paid / CR=Received),
        PayerVpa (sender UPI handle), PayeeVpa (receiver UPI handle),
        Time (ISO 8601, e.g. "2026-05-23T15:23:45.359Z"), Bank, AccountNumber

    The HTML table also has a Status column (SUCCESS/FAILURE) which we
    extract from the <td> cells and join back by transaction Id.

    FAILURE transactions are skipped — money never actually moved.
    """

    def _extract_xml_from_html(self, html: str) -> str:
        """Pull the XML string out of the JS var DATA = '...'; block."""
        m = re.search(r"var DATA\s*=\s*'(.+?)';", html, re.DOTALL)
        if not m:
            raise ValueError("Could not find 'var DATA' block in BHIM HTML file.")
        return m.group(1).replace('\\"', '"')

    def _extract_status_map(self, html: str) -> dict:
        """
        Parse the HTML table to get {transaction_id: status} mapping.
        Columns: Date, Time, Bank, Account, Sender, Receiver,
                 Payment ID, Pay/Collect, Amount, DR/CR, Status
        """
        status_map = {}
        rows = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td>(.*?)</td>', row)
            if len(cells) == 11:
                txn_id = cells[6].strip()
                status = cells[10].strip()
                status_map[txn_id] = status
        return status_map

    def _extract_name_from_vpa(self, vpa: str) -> str:
        """
        VPA format: 'xxxxx98414@upi(Shivang Singh Negi)'
        Extract the display name in parentheses, else return the handle.
        """
        m = re.search(r'\((.+?)\)$', vpa)
        if m:
            return m.group(1).strip()
        return vpa.split('(')[0].strip()

    def extract_from_pdf(self, file_path: str) -> list:
        """
        BHIM exports HTML, not PDF. This method accepts .html paths.
        Named extract_from_pdf to satisfy the BaseParser interface.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()

        xml_str    = self._extract_xml_from_html(html)
        status_map = self._extract_status_map(html)
        root       = ET.fromstring(xml_str)

        results = []

        for txn in root.findall('.//Transaction'):
            txn_id     = txn.get('Id', '')
            amount_str = txn.get('Amount', '0')
            benefit    = txn.get('BenefitType', '')   # DR or CR
            payer_vpa  = txn.get('PayerVpa', '')
            payee_vpa  = txn.get('PayeeVpa', '')
            time_str   = txn.get('Time', '')
            bank       = txn.get('Bank', '')
            account    = txn.get('AccountNumber', '')
            status     = status_map.get(txn_id, 'UNKNOWN')

            # Skip FAILURE transactions — money never moved
            if status == 'FAILURE':
                continue

            # Parse ISO 8601 UTC timestamp → local naive datetime
            txn_dt   = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            txn_dt   = txn_dt.astimezone(tz=None).replace(tzinfo=None)
            txn_date = txn_dt.date()
            txn_time = txn_dt.time()

            amount = float(amount_str)

            # DR = debit = money went out (Paid)
            # CR = credit = money came in (Received)
            if benefit == 'DR':
                txn_type = 'Paid'
                paid_to  = self._extract_name_from_vpa(payee_vpa)
                paid_by  = f"{bank} {account}"
                upi_id   = payee_vpa.split('(')[0].strip()
            else:
                txn_type = 'Received'
                paid_by  = self._extract_name_from_vpa(payer_vpa)
                paid_to  = f"{bank} {account}"
                upi_id   = payer_vpa.split('(')[0].strip()

            results.append(Transaction(
                transaction_date=txn_date,
                transaction_time=txn_time,
                transaction_datetime=txn_dt,
                transaction_type=txn_type,
                paid_to=paid_to,
                paid_by=paid_by,
                amount=amount,
                upi_transaction_id=txn_id,
                provider='bhim',
                upi_id=upi_id or None,
                note=status,   # store SUCCESS/UNKNOWN in note column
            ))

        # deduplicate handles duplicate XML entries in the file
        unique = self.deduplicate(results)
        print(f"  [BHIM] {len(unique)} transactions extracted")
        return unique

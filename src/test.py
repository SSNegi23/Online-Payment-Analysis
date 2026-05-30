import re
import pdfplumber

with pdfplumber.open('D:\Development\OnlinePaymentAnalysisProject\data\Paytm_UPI_Statement_27_May\'25_-_26_May\'26.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)


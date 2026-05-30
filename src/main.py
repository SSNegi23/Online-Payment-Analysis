import logging
import os
from pathlib import Path
from parsers import get_parser, supported_providers
from db import setup_table, insert_transactions

os.makedirs("../logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("../logs/etl.log"),
        logging.StreamHandler()
    ]
)

DATA_DIR = Path("../data")


def prompt_pdf_provider_mapping(pdfs: list[Path]) -> dict[Path, str]:
    """
    Ask the user which provider each PDF belongs to.
    Returns a dict of {pdf_path: provider_name}.
    """
    providers = supported_providers()
    print(f"\n📱 Supported providers: {', '.join(providers)}")
    print("─" * 50)

    mapping = {}
    for pdf in pdfs:
        while True:
            choice = input(f"Provider for '{pdf.name}': ").strip().lower()
            if choice in providers:
                mapping[pdf] = choice
                break
            else:
                print(f"  ❌ Invalid. Choose from: {', '.join(providers)}")

    # Confirm before proceeding
    print("\n📋 Confirmed mapping:")
    for pdf, provider in mapping.items():
        print(f"  {pdf.name:50s} → {provider}")
    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        return {}

    return mapping


def main():
    setup_table()

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        logging.warning("No PDFs found in data/")
        return

    print(f"\nFound {len(pdfs)} PDF(s) in data/:")
    for i, p in enumerate(pdfs, 1):
        print(f"  {i}. {p.name}")

    mapping = prompt_pdf_provider_mapping(pdfs)
    if not mapping:
        return

    print()
    total_extracted = 0
    total_inserted  = 0

    for pdf, provider in mapping.items():
        logging.info(f"Processing: {pdf.name} [{provider}]")
        try:
            parser   = get_parser(provider)
            txns     = parser.extract_from_pdf(pdf)
            inserted = insert_transactions(txns)
            logging.info(f"  Extracted {len(txns)} | Inserted {inserted} new rows")
            total_extracted += len(txns)
            total_inserted  += inserted
        except Exception as e:
            logging.error(f"  Failed to process {pdf.name}: {e}")

    print(f"\n✅ Done — {total_extracted} total extracted, {total_inserted} new rows inserted.")


if __name__ == "__main__":
    main()

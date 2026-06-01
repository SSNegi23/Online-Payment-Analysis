import logging
import os
from pathlib import Path
from parsers import get_parser, supported_providers, valid_extensions_for
from db import setup_table, insert_transactions

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
os.makedirs(LOGS_DIR, exist_ok=True) 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(str(LOGS_DIR / "etl.log")),
        logging.StreamHandler()
    ]
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" 
SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm"}


def scan_files() -> list[Path]:
    """Return all supported files in data/ sorted by name."""
    files = [
        f for f in sorted(DATA_DIR.iterdir())
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return files


def prompt_pdf_provider_mapping(files: list[Path]) -> dict[Path, str]:
    """
    Ask the user which provider each file belongs to.
    Validates that the provider supports the file's extension.
    Returns {file_path: provider_name}.
    """
    providers = supported_providers()
    print(f"\n📱 Supported providers: {', '.join(providers)}")
    print("─" * 55)

    mapping = {}
    for f in files:
        ext = f.suffix.lower()
        while True:
            choice = input(f"Provider for '{f.name}': ").strip().lower()
            if choice not in providers:
                print(f"  ❌ Invalid. Choose from: {', '.join(providers)}")
                continue
            valid_exts = valid_extensions_for(choice)
            if ext not in valid_exts:
                print(f"  ❌ '{choice}' expects {valid_exts} files, not '{ext}'")
                continue
            mapping[f] = choice
            break

    # Confirm
    print("\n📋 Confirmed mapping:")
    for f, provider in mapping.items():
        print(f"  {f.name:55s} → {provider}")
    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        return {}

    return mapping


def main():
    setup_table()

    files = scan_files()
    if not files:
        logging.warning(f"No supported files found in data/ (looked for {SUPPORTED_EXTENSIONS})")
        return

    print(f"\nFound {len(files)} file(s) in data/:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")

    mapping = prompt_pdf_provider_mapping(files)
    if not mapping:
        return

    print()
    total_extracted = 0
    total_inserted  = 0

    for file_path, provider in mapping.items():
        logging.info(f"Processing: {file_path.name} [{provider}]")
        try:
            parser   = get_parser(provider)
            txns     = parser.extract_from_pdf(file_path)  # all parsers use this method
            inserted = insert_transactions(txns)
            logging.info(f"  Extracted {len(txns)} | Inserted {inserted} new rows")
            total_extracted += len(txns)
            total_inserted  += inserted
        except Exception as e:
            logging.error(f"  Failed to process {file_path.name}: {e}", exc_info=True)

    print(f"\n✅ Done — {total_extracted} total extracted, {total_inserted} new rows inserted.")


if __name__ == "__main__":
    main()

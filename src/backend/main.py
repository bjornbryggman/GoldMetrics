# Copyright (C) 2025 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
Exports data from the 'World of Warcraft' addon 'TradeSkillMaster'.

This module includes:
- Configuration constants for file paths and output directories.
- Core functions for importing TSM data, decoding compressed strings, and exporting to Parquet.
- Data generation functions for extracting accounting, groups, operations, and item database records.
- Main execution function that orchestrates the complete export process.
"""

import json
import base64
import zlib
from pathlib import Path
from collections.abc import Iterator
import polars as pl
from structlog import stdlib

from slpp import slpp as lua

log = stdlib.get_logger(__name__)


# ===================================== #
#             Configuration             #
# ===================================== #


# IMPORTANT: Update this path to point to YOUR WoW account's WTF folder.
WOW_WTF_PATH = Path(
    r"C:\Ascension Launcher\resources\epoch_live\WTF\Account\BJORN.BRYGGMAN@GMAIL.COM"
)
LUA_FILE_PATH = WOW_WTF_PATH / "SavedVariables" / "TradeSkillMaster.lua"
OUTPUT_DIR = Path("tsm_exports")


# ====================================== #
#             Core Functions             #
# ====================================== #


def import_tsm_data(path: Path) -> dict:
    """
    Import and parse `TradeSkillMaster` data.

    This function reads the Lua file from the specified path and parses it
    using the SLPP library to convert Lua table syntax to Python dictionaries.

    Args:
        - path: The file path to the TradeSkillMaster.lua file.

    Returns:
        - dict: The parsed TSM database as a Python dictionary.

    Raises:
        - FileNotFoundError: If the specified file path does not exist.
        - UnicodeDecodeError: If the file cannot be decoded using UTF-8.
        - Exception: If the Lua parsing fails.
    """
    try:
        log.debug("[Process] Attempting to import TSM data...")
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()

        # Remove the variable declaration and parse the Lua table
        cleaned_data = data.replace("TradeSkillMasterDB = ", "", 1)
        parsed_data = lua.decode(cleaned_data)

        log.info("[Event] Successfully imported TSM data.")
        return parsed_data

    except FileNotFoundError:
        log.error("[Error] TSM file not found.")
        raise
    except UnicodeDecodeError:
        log.error("[Error] Failed to decode TSM file.")
        raise
    except Exception:
        log.error("[Error] Failed to parse TSM data.")
        raise


def decode_tsm_string(encoded: str) -> dict | list | None:
    try:
        compressed = base64.b64decode(encoded)
        return lua.decode(zlib.decompress(compressed).decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Decode failed: {e}")
        return None


def export_to_parquet(path: Path, rows: Iterator[dict]) -> None:
    """
    Consumes an iterator of rows and writes them to a Parquet file.

    This function creates a Polars DataFrame from the provided row iterator
    and exports it to a Parquet file. If no rows are provided, the write
    operation is skipped.

    Args:
        - path: The full path (including filename) where the Parquet file should be saved.
        - rows: An iterator yielding dictionaries, where each dictionary represents a row of data.
    """
    df = pl.DataFrame(rows)

    if df.height == 0:
        print(f"⚪️ {path.name} (0 rows, skipping write)")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    print(f"✅ {path.name} ({df.height} rows)")


# ================================================= #
#             Data Generation Functions             #
# ================================================= #


def generate_accounting_rows(db: dict) -> Iterator[dict]:
    """
    Yields each TradeSkillMaster (TSM) accounting record as a dictionary.

    This generator iterates through the 'accountingDB' section of the TSM database,
    decoding and flattening accounting records (sales, purchases, auctions, cancels)
    into individual dictionaries, each including 'factionrealm' and 'record_type'.

    Args:
        - db: The main TradeSkillMasterDB dictionary.

    Yields:
        - dict: A dictionary representing a single accounting record.
    """
    for fr, frdata in db.get("factionrealm", {}).items():
        acc_db = frdata.get("accountingDB", {})
        for kind in ("sales", "purchases", "auctions", "cancels"):
            encoded_data = acc_db.get(kind)
            if not encoded_data:
                continue

            decoded = decode_tsm_string(encoded_data)
            if isinstance(decoded, list):
                for r in decoded:
                    if isinstance(r, dict):
                        yield {"factionrealm": fr, "record_type": kind, **r}


def generate_groups_rows(db: dict) -> Iterator[dict]:
    for fr, frdata in db.get("factionrealm", {}).items():
        groups = frdata.get("groups", {})
        for name, gdata in groups.items():
            yield {"factionrealm": fr, "group": name, **(gdata or {})}


def generate_operations_rows(db: dict) -> Iterator[dict]:
    """Yields each TSM operation as a dictionary."""
    for profile, pdata in db.get("profiles", {}).items():
        ops = pdata.get("operations", {})
        for module, odict in ops.items():
            for opname, odata in odict.items():
                yield {
                    "profile": profile,
                    "module": module,
                    "operation": opname,
                    **(odata or {}),
                }


def generate_itemdb_rows(db: dict) -> Iterator[dict]:
    """Yields each TSM itemDB entry as a dictionary."""
    for fr, frdata in db.get("factionrealm", {}).items():
        itemdb = frdata.get("itemDB")
        if not itemdb:
            continue

        decoded = decode_tsm_string(itemdb)
        if isinstance(decoded, dict):
            for item, idata in decoded.items():
                if isinstance(idata, dict):
                    yield {"factionrealm": fr, "itemString": item, **idata}


# ============================ #
#             Main             #
# ============================ #


def main():
    """Main script execution."""
    if not LUA_FILE_PATH.exists():
        print(f"❌ Error: TSM Lua file not found at '{LUA_FILE_PATH}'")
        print("Please update the WOW_WTF_PATH variable in the script.")
        return

    tsm_db = import_tsm_data(LUA_FILE_PATH)

    # Optional: Dump full JSON for inspection
    json_path = OUTPUT_DIR / "tsm_full.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tsm_db, f, indent=2, ensure_ascii=False)
    print(f"✅ Full database dumped to {json_path}")

    # Define the export "jobs"
    export_jobs = [
        {
            "filename": "tsm_accounting.parquet",
            "generator_func": generate_accounting_rows,
        },
        {"filename": "tsm_groups.parquet", "generator_func": generate_groups_rows},
        {
            "filename": "tsm_operations.parquet",
            "generator_func": generate_operations_rows,
        },
        {"filename": "tsm_itemdb.parquet", "generator_func": generate_itemdb_rows},
    ]

    # Process all jobs
    print("\n--- Starting TSM Data Export ---")
    for job in export_jobs:
        rows_iterator = job["generator_func"](tsm_db)
        output_path = OUTPUT_DIR / job["filename"]
        export_to_parquet(output_path, rows_iterator)
    print("\n--- Export Complete ---")


if __name__ == "__main__":
    main()

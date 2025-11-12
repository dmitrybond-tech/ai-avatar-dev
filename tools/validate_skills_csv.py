#!/usr/bin/env python3
"""Validate skills CSV file structure and content.

Checks:
- Header has exactly 10 columns
- Every quoted field is properly closed
- Reports first broken line index
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def validate_csv(csv_path: Path) -> tuple[bool, list[str]]:
    """Validate CSV file and return (is_valid, errors)."""
    errors: list[str] = []
    
    if not csv_path.exists():
        return False, [f"CSV file does not exist: {csv_path}"]
    
    expected_headers = [
        "Title EN", "Bullets EN", "Bullets RU", "Examples EN", "Examples RU",
        "Short EN", "Short RU", "Slug", "Tags", "Title RU"
    ]
    expected_col_count = len(expected_headers)
    
    try:
        with csv_path.open(encoding="utf-8-sig") as f:
            # Read first line to check headers
            first_line = f.readline()
            if not first_line:
                return False, ["CSV file is empty"]
            
            # Reset and use csv reader
            f.seek(0)
            reader = csv.reader(f)
            
            # Check header
            try:
                header = next(reader)
            except StopIteration:
                return False, ["CSV file has no header row"]
            
            if len(header) != expected_col_count:
                errors.append(
                    f"Header has {len(header)} columns, expected {expected_col_count}. "
                    f"Found: {header}"
                )
            
            # Check each row
            line_num = 2  # Start at 2 (after header)
            for row in reader:
                if len(row) != expected_col_count:
                    errors.append(
                        f"Line {line_num} has {len(row)} fields, expected {expected_col_count}. "
                        f"First few fields: {row[:3] if len(row) >= 3 else row}"
                    )
                    # Stop at first error for now (can be made configurable)
                    if errors:
                        break
                line_num += 1
            
            if not errors:
                # Try to read with pandas to check multiline quoted fields
                try:
                    import pandas as pd
                    df = pd.read_csv(
                        csv_path,
                        encoding="utf-8-sig",
                        engine="python",
                        quotechar='"',
                        skipinitialspace=True,
                        on_bad_lines="skip"
                    )
                    if df.empty:
                        errors.append("CSV parsed successfully but contains no data rows")
                    elif len(df.columns) != expected_col_count:
                        errors.append(
                            f"Parsed CSV has {len(df.columns)} columns, expected {expected_col_count}"
                        )
                except ImportError:
                    # pandas not available, skip advanced validation
                    pass
                except Exception as exc:
                    errors.append(f"Pandas validation failed: {exc}")
    
    except UnicodeDecodeError as exc:
        return False, [f"Failed to decode CSV as UTF-8: {exc}"]
    except Exception as exc:
        return False, [f"Error reading CSV: {exc}"]
    
    return len(errors) == 0, errors


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        csv_path = Path("apps/miniapp-api/data/skills.csv")
    else:
        csv_path = Path(sys.argv[1])
    
    is_valid, errors = validate_csv(csv_path)
    
    if is_valid:
        print(f"[OK] CSV file is valid: {csv_path}")
        sys.exit(0)
    else:
        print(f"[FAIL] CSV file validation failed: {csv_path}")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()


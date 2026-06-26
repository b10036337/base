"""Fetch TWSE BWIBBU daily data and keep a CSV history up to date.

The script can bootstrap the full history from 2006-01-01 and, on later runs,
append only missing dates after the latest date already present in the output
CSV. It is designed to run locally or from GitHub Actions on a daily schedule.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

BASE_URL = "https://www.twse.com.tw/exchangeReport/BWIBBU_d"
DEFAULT_START_DATE = "20060101"
DEFAULT_OUTPUT = "bwibbu_all.csv"
REQUEST_TIMEOUT_SECONDS = 10
SLEEP_SECONDS = 0.3


def fetch_day(date_str: str) -> pd.DataFrame | None:
    """Fetch one trading day's BWIBBU data.

    Args:
        date_str: Date in YYYYMMDD format.

    Returns:
        A DataFrame for the date, or None when TWSE has no data for the day
        (for example weekends, holidays, or dates before available history).
    """
    params = {"response": "json", "date": date_str, "selectType": "ALL"}

    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()

        if data.get("stat") != "OK" or not data.get("data"):
            return None

        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date_str
        return df
    except Exception as exc:  # noqa: BLE001 - keep batch jobs moving and log the date.
        print(f"error {date_str}: {exc}")
        return None


def date_range(start_date: datetime, end_date: datetime) -> Iterable[datetime]:
    """Yield every date from start_date through end_date, inclusive."""
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def latest_date_from_csv(output_path: Path) -> str | None:
    """Return the latest YYYYMMDD date already present in the CSV, if any."""
    if not output_path.exists() or output_path.stat().st_size == 0:
        return None

    try:
        existing_dates = pd.read_csv(output_path, usecols=["date"], dtype={"date": str})
    except (ValueError, pd.errors.EmptyDataError):
        return None

    if existing_dates.empty:
        return None

    return existing_dates["date"].dropna().max()


def fetch_history(start_date: str = DEFAULT_START_DATE, end_date: str | None = None) -> pd.DataFrame:
    """Fetch all available BWIBBU data between start_date and end_date."""
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d") if end_date else datetime.today()

    all_data: list[pd.DataFrame] = []
    for day in date_range(start, end):
        date_str = day.strftime("%Y%m%d")
        print("fetch:", date_str)

        df = fetch_day(date_str)
        if df is not None:
            all_data.append(df)

        time.sleep(SLEEP_SECONDS)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


def update_history(output_path: Path, start_date: str, end_date: str | None = None) -> bool:
    """Append missing data to output_path.

    Returns True when the CSV was created or changed; otherwise False.
    """
    latest_date = latest_date_from_csv(output_path)
    if latest_date:
        next_date = (datetime.strptime(latest_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        start_date = max(start_date, next_date)

    effective_end = end_date or datetime.today().strftime("%Y%m%d")
    if start_date > effective_end:
        print(f"{output_path} is already up to date through {latest_date}.")
        return False

    new_data = fetch_history(start_date=start_date, end_date=end_date)
    if new_data.empty:
        print("No new rows fetched.")
        return False

    if output_path.exists() and output_path.stat().st_size > 0:
        existing = pd.read_csv(output_path, dtype={"date": str})
        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "證券代號"], keep="last")
    else:
        combined = new_data

    combined = combined.sort_values(["date", "證券代號"], kind="stable")
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(combined)} rows to {output_path}.")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and update TWSE BWIBBU history CSV.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Start date in YYYYMMDD format.")
    parser.add_argument("--end-date", default=None, help="End date in YYYYMMDD format; defaults to today.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    update_history(Path(args.output), args.start_date, args.end_date)


if __name__ == "__main__":
    main()

# TWSE BWIBBU History

This repository fetches historical TWSE BWIBBU daily data from `https://www.twse.com.tw/exchangeReport/BWIBBU_d` and stores it in `bwibbu_all.csv`.

## Local usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Fetch the full history from 2006-01-01 and write/update `bwibbu_all.csv`:

```bash
python fetch_bwibbu.py
```

Useful options:

```bash
python fetch_bwibbu.py --start-date 20060101 --end-date 20240630 --output bwibbu_all.csv
```

The script is incremental: if `bwibbu_all.csv` already exists, it starts from the day after the latest `date` in the CSV.

## Daily GitHub update

The workflow in `.github/workflows/update-bwibbu.yml` runs once per day and can also be started manually from the GitHub Actions tab. When new rows are fetched, the workflow commits the updated `bwibbu_all.csv` back to the current branch.

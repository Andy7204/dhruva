"""Download official NSE Total Return Index history (niftyindices.com) and gold in INR.

TRI includes reinvested dividends. Index membership is point-in-time, so there is
no survivorship bias from using today's constituent list. Values before each
index's launch date are NSE back-calculations; see README.md.

    python research/v2/fetch_indices.py
"""
import csv, json, time, urllib.request
from datetime import date, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parents[2]/'data'/'indices'
INDICES = ['NIFTY 50','NIFTY NEXT 50','NIFTY 100','NIFTY 200','NIFTY 500','NIFTY MIDCAP 150',
    'NIFTY SMALLCAP 250','NIFTY MIDCAP 100','NIFTY200 MOMENTUM 30','NIFTY MIDCAP150 MOMENTUM 50',
    'NIFTY500 MOMENTUM 50','NIFTY ALPHA 50','NIFTY100 LOW VOLATILITY 30','NIFTY200 QUALITY 30',
    'NIFTY100 QUALITY 30','NIFTY50 VALUE 20','NIFTY200 VALUE 30','NIFTY500 VALUE 50',
    'NIFTY ALPHA LOW-VOLATILITY 30','NIFTY QUALITY LOW-VOLATILITY 30','NIFTY MIDCAP150 QUALITY 50',
    'NIFTY200 ALPHA 30','NIFTY100 ALPHA 30','NIFTY DIVIDEND OPPORTUNITIES 50','NIFTY 1D RATE INDEX',
    'NIFTY 8-13 YR G-SEC','NIFTY SMALLCAP250 MOMENTUM QUALITY 100','NIFTY500 MULTICAP MOMENTUM QUALITY 50',
    'NIFTY100 EQUAL WEIGHT','NIFTY50 EQUAL WEIGHT']


def post(name, start, end):
    body = json.dumps({'cinfo': "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (name, start, end, name)}).encode()
    req = urllib.request.Request('https://www.niftyindices.com/BackPage/getTotalReturnIndexString', data=body,
        headers={'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'Mozilla/5.0'})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            time.sleep(3*(attempt+1))
    raise RuntimeError(f'fetch failed {name} {start}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in INDICES:
        rows = {}
        for year in range(1999, date.today().year+1, 2):
            data = post(name, f'01-Jan-{year}', f'31-Dec-{year+1}')
            for r in data if isinstance(data, list) else []:
                try:
                    rows[datetime.strptime(r['Date'], '%d %b %Y').date().isoformat()] = float(str(r['TotalReturnsIndex']).replace(',', ''))
                except (KeyError, ValueError):
                    pass
            time.sleep(0.4)
        path = OUT/(name.replace(' ', '_').replace('-', '_')+'.csv')
        with path.open('w', newline='') as f:
            w = csv.writer(f); w.writerow(['date', 'tri'])
            for d in sorted(rows): w.writerow([d, rows[d]])
        report[name] = [min(rows), max(rows), len(rows)] if rows else None
        print(name, report[name], flush=True)
    (OUT/'fetch_report.json').write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()

import os, re, json
from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF

app = Flask(__name__)
CORS(app)  # allow browser calls from any origin

# ── KEYWORD ALIASES ─────────────────────────────────────────────
ALIASES = {
    "revenue_from_operations": ["revenue from operations","net revenue","turnover","net sales","revenue from contracts","income from operations","gross revenue"],
    "other_income":            ["other income","non-operating income","miscellaneous income"],
    "cogs":                    ["cost of goods sold","cost of materials","cost of sales","purchases","material consumed","raw material","cost of revenue","cogs"],
    "employee_expenses":       ["employee benefit","staff cost","salaries","wages","personnel expense","remuneration"],
    "other_expenses":          ["other expense","selling","distribution","administrative","general expense","overhead","indirect expense"],
    "finance_cost":            ["finance cost","interest expense","interest paid","borrowing cost","bank charge","financial charge"],
    "depreciation":            ["depreciation","amortisation","amortization","d&a","depletion"],
    "tax_expense":             ["tax expense","income tax","provision for tax","current tax","deferred tax"],
    "pat":                     ["profit after tax","net profit","pat","profit for the year","profit for the period","net income","net earnings"],
    "tangible_assets":         ["tangible asset","property plant","ppe","fixed asset","net block","plant and equipment"],
    "cwip":                    ["capital work","cwip","capital wip","work-in-progress"],
    "intangible_assets":       ["intangible asset","goodwill","brand","software asset"],
    "inventories":             ["inventor","stock-in-trade","stock in trade","finished goods","raw material stock"],
    "debtors":                 ["trade receivable","debtor","sundry debtor","account receivable"],
    "cash":                    ["cash and cash equivalent","cash and bank","bank balance","cash balance"],
    "short_term_loans":        ["short-term loan","short term loan","other current asset","advance recoverable","prepaid"],
    "equity_share_capital":    ["equity share capital","share capital","paid-up capital","paid up capital"],
    "reserves_surplus":        ["reserve and surplus","reserves & surplus","retained earning","other equity","free reserve"],
    "long_term_borrowings":    ["long-term borrowing","long term borrowing","term loan","secured loan","unsecured loan","non-current borrowing"],
    "short_term_borrowings":   ["short-term borrowing","short term borrowing","working capital loan","cash credit","cc limit","overdraft","od limit","bank od"],
    "trade_payables":          ["trade payable","creditor","sundry creditor","account payable"],
    "other_current_liabilities":["other current liab","other liab","advance from customer","statutory due","other payable"],
}

def clean_label(text):
    return re.sub(r'[^a-z0-9 ]', '', text.lower().strip())

def match_key(label):
    for key, aliases in ALIASES.items():
        for a in aliases:
            if a in label:
                return key
    return None

def parse_number(s):
    """Parse Indian number format, handle lakhs/crores."""
    s = str(s).replace(',', '').strip()
    s = re.sub(r'\((.+?)\)', r'-\1', s)  # (123) → -123
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        return float(s)
    except:
        return None

def extract_year(text):
    """Find fiscal year from text."""
    # Look for "Year ended 31 March 2024" or "FY 2023-24" or "2023-24"
    m = re.search(r'(?:year ended|as at|march|31st march)[^\d]*(\d{4})', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'20(\d{2})-(\d{2})', text)
    if m:
        return 2000 + int(m.group(1)) + 1  # 2023-24 → 2024
    m = re.search(r'\b(20\d{2})\b', text)
    if m:
        return int(m.group(1))
    return None

def extract_company(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:20]:
        if len(line) > 5 and len(line) < 100 and re.search(r'(?:pvt|ltd|limited|llp|inc|corp)', line, re.IGNORECASE):
            return line
    return lines[0] if lines else "Unknown"

def pdf_to_data(pdf_bytes, filename=""):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()

    year = extract_year(full_text) or extract_year(filename)
    company = extract_company(full_text)

    pl = {}
    bs_assets = {}
    bs_liabilities = {}

    PL_KEYS    = ["revenue_from_operations","other_income","cogs","employee_expenses","other_expenses","finance_cost","depreciation","tax_expense","pat"]
    ASSET_KEYS = ["tangible_assets","cwip","intangible_assets","inventories","debtors","cash","short_term_loans"]
    LIAB_KEYS  = ["equity_share_capital","reserves_surplus","long_term_borrowings","short_term_borrowings","trade_payables","other_current_liabilities"]

    lines = full_text.split('\n')
    for line in lines:
        label = clean_label(line)
        if not label:
            continue
        # Extract all numbers from the line
        nums_raw = re.findall(r'[\-\(]?[\d,]+\.?\d*\)?', line)
        nums = []
        for n in nums_raw:
            v = parse_number(n)
            if v is not None and abs(v) > 0.01:
                nums.append(v)
        if not nums:
            continue
        key = match_key(label)
        if not key:
            continue
        # Store only first two numbers (current year, previous year)
        vals = nums[:2]
        if key in PL_KEYS and key not in pl:
            pl[key] = vals
        elif key in ASSET_KEYS and key not in bs_assets:
            bs_assets[key] = vals
        elif key in LIAB_KEYS and key not in bs_liabilities:
            bs_liabilities[key] = vals

    # If document has 2 columns (current + previous year), split into two records
    has_prev = any(
        len(v) >= 2 for d in [pl, bs_assets, bs_liabilities] for v in d.values()
    )

    results = []
    if has_prev and year:
        # current year
        results.append({
            "year": year,
            "company": company,
            "pl":            {k: [v[0]] for k, v in pl.items()},
            "bs_assets":     {k: [v[0]] for k, v in bs_assets.items()},
            "bs_liabilities":{k: [v[0]] for k, v in bs_liabilities.items()},
        })
        # previous year
        results.append({
            "year": year - 1,
            "company": company,
            "pl":            {k: [v[1]] for k, v in pl.items() if len(v) >= 2},
            "bs_assets":     {k: [v[1]] for k, v in bs_assets.items() if len(v) >= 2},
            "bs_liabilities":{k: [v[1]] for k, v in bs_liabilities.items() if len(v) >= 2},
        })
    else:
        results.append({
            "year": year,
            "company": company,
            "pl":            {k: [v[0]] for k, v in pl.items()},
            "bs_assets":     {k: [v[0]] for k, v in bs_assets.items()},
            "bs_liabilities":{k: [v[0]] for k, v in bs_liabilities.items()},
        })

    return results


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/extract-financials", methods=["POST"])
def extract_financials():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    all_results = []
    for f in files:
        try:
            data = pdf_to_data(f.read(), f.filename)
            all_results.extend(data)
        except Exception as e:
            all_results.append({"error": str(e), "filename": f.filename})

    return jsonify({"results": all_results})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8092))
    app.run(host="0.0.0.0", port=port)

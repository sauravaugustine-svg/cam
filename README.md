# CAM Server — Railway Deployment Guide

## What this does
Python Flask server that extracts financials from PDFs using PyMuPDF (no API key needed).

---

## Deploy to Railway (5 minutes)

### Step 1 — Create GitHub repo
1. Go to https://github.com/new
2. Create a new **private** repo called `cam-server`
3. Upload these 4 files:
   - `main.py`
   - `requirements.txt`
   - `Procfile`
   - `railway.json`

### Step 2 — Deploy on Railway
1. Go to https://railway.app and sign up (free tier works)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Connect your GitHub and select `cam-server`
4. Railway auto-detects Python and deploys

### Step 3 — Get your URL
1. In Railway dashboard, click your service → **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Your URL will look like: `https://cam-server-production.up.railway.app`

### Step 4 — Connect the HTML
1. Open `cam_v2.html` in your browser
2. Click the server status indicator (top right)
3. Paste your Railway URL → press OK
4. The dot turns **green** when connected ✓

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/extract-financials` | POST | Upload PDF, returns JSON |

### Example response
```json
{
  "results": [
    {
      "year": 2024,
      "company": "Acme Industries Pvt Ltd",
      "pl": {
        "revenue_from_operations": [11500],
        "pat": [770]
      },
      "bs_assets": { ... },
      "bs_liabilities": { ... }
    }
  ]
}
```

---

## Free tier limits
- Railway free tier: 500 hours/month (enough for ~20 PDFs/day)
- No rate limits on extraction
- Upgrade to Hobby ($5/mo) for always-on

## Local testing
```bash
pip install flask flask-cors PyMuPDF gunicorn
python main.py
# Server runs on http://localhost:8092
```

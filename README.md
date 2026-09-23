# SecureBank — AI Fraud & Coercion Protection Prototype

A safe banking-app prototype for testing an AI security layer. It uses fake accounts and fake money only.

## Features
- Demo banking dashboard
- PIN login
- Demo balance and transfers
- Biometric verification flag
- Call-transcript scam analysis
- Coercion detection
- Payment risk engine
- Automatic payment pause/block for high-risk signals

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

Demo credentials:
- Username: `thabiso`
- PIN: `1234`

This is not connected to FNB, ABSA, or any real bank.

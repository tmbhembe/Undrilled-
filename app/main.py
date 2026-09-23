from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
from .ai_detector import analyze_transcript

app = FastAPI(title="SecureBank", version="0.2.0")

USERS = {"thabiso": {"pin": "1234", "name": "Thabiso", "balance": 25000.00}}

class Login(BaseModel):
    username: str
    pin: str = Field(min_length=4, max_length=8)

class Payment(BaseModel):
    username: str
    recipient: str
    amount: float = Field(gt=0)
    biometric_verified: bool = False
    scam_risk: float = Field(default=0.0, ge=0, le=1)
    coercion_risk: float = Field(default=0.0, ge=0, le=1)

class CallAnalysis(BaseModel):
    transcript: str = Field(min_length=1, max_length=10000)

class SecurePayment(BaseModel):
    username: str
    recipient: str
    amount: float = Field(gt=0)
    biometric_verified: bool = False
    call_transcript: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTML

@app.post("/api/login")
def login(data: Login):
    user = USERS.get(data.username)
    if not user or user["pin"] != data.pin:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    return {"authenticated": True, "name": user["name"], "balance": user["balance"]}

@app.post("/api/security/analyze-call")
def analyze_call(data: CallAnalysis):
    return {**analyze_transcript(data.transcript), "demo_only": True}

@app.post("/api/security/payment-check")
def payment_check(data: Payment):
    risk = max(data.scam_risk, data.coercion_risk)
    reasons = []
    if data.scam_risk >= .70: reasons.append("Potential scam indicators detected")
    if data.coercion_risk >= .70: reasons.append("Potential coercion indicators detected")
    if data.amount >= 10000:
        risk = max(risk, .65); reasons.append("Large demo transaction")
    if not data.biometric_verified: reasons.append("Biometric verification required")
    if risk >= .70: status, level = "BLOCKED", "HIGH"
    elif risk >= .40 or not data.biometric_verified: status, level = "STEP_UP_AUTH", "MEDIUM"
    else: status, level = "APPROVED", "LOW"
    return {"transaction_status": status, "risk_level": level,
            "risk_score": round(risk*100,1), "reasons": reasons, "demo_only": True}

@app.post("/api/security/analyze-payment")
def analyze_payment(data: SecurePayment):
    call = analyze_transcript(data.call_transcript or "")
    security = payment_check(Payment(
        username=data.username, recipient=data.recipient, amount=data.amount,
        biometric_verified=data.biometric_verified,
        scam_risk=call["scam_risk"], coercion_risk=call["coercion_risk"]))
    return {"call_analysis": call, "payment_security": security, "demo_only": True}

@app.post("/api/payments")
def make_payment(data: Payment):
    user = USERS.get(data.username)
    if not user: raise HTTPException(status_code=404, detail="Demo user not found")
    security = payment_check(data)
    if security["transaction_status"] != "APPROVED": return security
    if data.amount > user["balance"]: raise HTTPException(status_code=400, detail="Insufficient demo balance")
    user["balance"] -= data.amount
    return {"transaction_status":"COMPLETED","amount":data.amount,
            "recipient":data.recipient,"remaining_demo_balance":round(user["balance"],2),
            "demo_only":True}

HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SecureBank</title><style>
body{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;color:#18202a}
header{background:#075e54;color:white;padding:22px}main{max-width:900px;margin:25px auto;padding:0 16px}
.card{background:white;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 2px 12px #0001}
input,button{padding:12px;margin:5px;border-radius:8px;border:1px solid #ccd3d8}
button{background:#075e54;color:white;border:0;cursor:pointer}.danger{background:#a61b1b}
#result{white-space:pre-wrap}
</style></head><body><header><h1>SecureBank</h1><p>AI Fraud & Coercion Protection — DEMO</p></header>
<main><div class="card"><h2>Demo Login</h2><input id="u" value="thabiso"><input id="p" value="1234" type="password"><button onclick="login()">Login</button><div id="balance"></div></div>
<div class="card"><h2>Protected Transfer</h2>
<input id="recipient" placeholder="Recipient" value="demo-recipient"><input id="amount" type="number" value="2500">
<label><input id="bio" type="checkbox"> Biometric verified</label><br>
<textarea id="call" rows="5" style="width:95%" placeholder="Paste a permitted call transcript for the demo..."></textarea><br>
<button onclick="check()">Analyze & Check Payment</button><div id="result"></div></div>
<div class="card"><h3>How the protection works</h3><p>Call transcript → scam/coercion analysis → risk engine → biometric/step-up check → approve, pause, or block.</p><p><b>Demo only:</b> no real money or bank account is involved.</p></div></main>
<script>
async function login(){let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,pin:p.value})});let x=await r.json();balance.textContent=r.ok?'Welcome '+x.name+' — Demo balance: R'+x.balance.toFixed(2):x.detail}
async function check(){let r=await fetch('/api/security/analyze-payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,recipient:recipient.value,amount:+amount.value,biometric_verified:bio.checked,call_transcript:call.value})});result.textContent=JSON.stringify(await r.json(),null,2)}
</script></body></html>"""

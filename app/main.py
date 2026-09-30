"""The front door.

POST /analyze: raw email in, stamped verdict out.
GET /health: is the building awake? (for the heartbeat)
"""
from fastapi import FastAPI

from .schemas import AnalyzeRequest, Verdict
from .extractor import extract
from .classifier import classify
from .validator import validate

app = FastAPI(title="PhishSquad")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    email = extract(req.raw_email)
    evidence = []  # Station 2 stub — the detective squad arrives in Phase 3
    statement = classify(email, evidence)
    return validate(statement, lambda: classify(email, evidence))


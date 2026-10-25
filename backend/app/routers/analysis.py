import io
import pandas as pd
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from ..config import MAX_UPLOAD_BYTES
from ..ml.historical import load as load_history
from ..ml.pipeline import run
from ..security import current_user
from ..services.report import build_pdf

router = APIRouter()
LAST = {}  # latest analysis per user (in memory, used for the PDF report)

@router.post("/analyze")
def analyze(file: UploadFile = File(...), user=Depends(current_user)):
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (25 MB max)")
    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
        result = run(df, load_history())
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as e:
        raise HTTPException(400, str(e))
    LAST[user["name"]] = result
    return result

@router.post("/report")
def report_from_result(result: dict = Body(...), user=Depends(current_user)):
    """Builds a fresh PDF from the analysis the browser already has (works after server restarts)."""
    try:
        pdf = build_pdf(result, user["name"])
    except Exception as e:
        raise HTTPException(500, f"Could not build the PDF: {e}")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="smartaudit-report.pdf"'})

@router.get("/report")
def report(user=Depends(current_user)):
    result = LAST.get(user["name"])
    if not result:
        raise HTTPException(404, "Run an analysis first")
    return Response(build_pdf(result, user["name"]), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="smartaudit-report.pdf"'})

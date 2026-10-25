import io
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from ..config import MAX_UPLOAD_BYTES
from ..ml import historical as H
from ..ml.preprocess import clean
from ..security import current_user

router = APIRouter(prefix="/history")

@router.post("/upload")
def upload(file: UploadFile = File(...), user=Depends(current_user)):
    if user["role"] == "Viewer":
        raise HTTPException(403, "Viewers cannot upload historical data")
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (25 MB max)")
    try:
        df, _, _ = clean(pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False))
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as e:
        raise HTTPException(400, str(e))
    return H.store(df, file.filename or "history.csv", user["name"])

@router.get("/summary")
def summary(_=Depends(current_user)):
    return H.summary()

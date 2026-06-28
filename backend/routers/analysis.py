from fastapi import APIRouter, HTTPException
from backend.services.engine_bridge import analyze_ticker

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{ticker}")
def get_analysis(ticker: str):
    result = analyze_ticker(ticker.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    return result

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.repository_service import repository_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    repo_id: str


@router.post("/bugs")
def analyze_bugs(payload: AnalysisRequest) -> dict:
    findings = repository_service.get_repository(payload.repo_id)
    if not findings:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": payload.repo_id, "bugs": ["Potential hardcoded credentials in auth sample", "Missing error handling in sample service module"]}


@router.post("/improvements")
def analyze_improvements(payload: AnalysisRequest) -> dict:
    findings = repository_service.get_repository(payload.repo_id)
    if not findings:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": payload.repo_id, "improvements": ["Replace hardcoded credentials with config values", "Add explicit error handling"]}


@router.post("/report")
def analysis_report(payload: AnalysisRequest) -> dict:
    findings = repository_service.get_repository(payload.repo_id)
    if not findings:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repo_id": payload.repo_id, "maintainability_score": 72, "complexity_score": 35, "documentation_coverage": 78}

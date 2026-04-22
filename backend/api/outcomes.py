from fastapi import APIRouter
from pydantic import BaseModel

from learning.store import record_outcome, list_outcomes

router = APIRouter(prefix="/api")


class OutcomeRequest(BaseModel):
    scenario: str
    result: str
    learned: str
    category: str = "general"
    success: bool = True


class OutcomeResponse(BaseModel):
    id: str
    message: str


@router.post("/outcomes", response_model=OutcomeResponse)
async def create_outcome(body: OutcomeRequest) -> OutcomeResponse:
    oid = record_outcome(
        scenario=body.scenario,
        result=body.result,
        learned=body.learned,
        category=body.category,
        success=body.success,
    )
    return OutcomeResponse(id=oid, message="Outcome recorded and indexed.")


@router.get("/outcomes")
async def get_outcomes(limit: int = 50) -> list[dict]:
    return list_outcomes(limit=limit)

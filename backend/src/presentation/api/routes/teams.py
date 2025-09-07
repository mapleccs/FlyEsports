from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def teams_health():
    return {"status": "Teams service is healthy"}
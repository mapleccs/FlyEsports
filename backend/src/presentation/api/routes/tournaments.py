from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def tournaments_health():
    return {"status": "Tournaments service is healthy"}
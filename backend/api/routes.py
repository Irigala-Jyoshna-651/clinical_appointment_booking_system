from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config import get_settings
from backend.dependencies import get_agent
from backend.schemas import HealthResponse, OutboundCampaignRequest, VoiceChunk

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="running", app=settings.app_name, environment=settings.app_env)


@router.post("/campaigns/outbound")
async def start_outbound_campaign(payload: OutboundCampaignRequest) -> dict:
    agent = get_agent()
    response = await agent.handle_outbound_campaign(payload)
    return response.model_dump()


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket) -> None:
    agent = get_agent()
    await websocket.accept()
    try:
        while True:
            raw_payload = await websocket.receive_json()
            chunk = VoiceChunk.model_validate(raw_payload)
            response = await agent.handle_voice_turn(chunk)
            await websocket.send_json(response.model_dump())
    except WebSocketDisconnect:
        await agent.close_session(websocket)

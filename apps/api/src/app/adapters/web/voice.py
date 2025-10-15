"""Voice/TTS router."""
from fastapi import APIRouter, HTTPException
from app.schemas.chat import TTSRequest, TTSResponse
from app.services.tts import TTSService

router = APIRouter()


@router.post("/voice/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech."""
    try:
        service = TTSService()
        audio_url, duration = await service.text_to_speech(
            text=request.text,
            voice_preset=request.voice_preset,
        )
        
        return TTSResponse(
            audio_url=audio_url,
            duration_sec=duration,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


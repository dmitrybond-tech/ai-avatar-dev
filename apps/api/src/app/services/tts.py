"""Text-to-speech service."""
import struct
import wave
import math
import uuid
from pathlib import Path
from typing import Optional
from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class TTSProvider:
    """Base TTS provider interface."""
    
    async def synthesize(
        self,
        text: str,
        voice: str = "default",
    ) -> tuple[Path, float]:
        """
        Synthesize speech from text.
        
        Returns: (audio_file_path, duration_seconds)
        """
        raise NotImplementedError


class StubTTSProvider(TTSProvider):
    """Stub TTS provider that generates a simple beep tone."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def synthesize(
        self,
        text: str,
        voice: str = "default",
    ) -> tuple[Path, float]:
        """Generate a short beep WAV file."""
        audio_id = uuid.uuid4().hex[:12]
        output_path = self.data_dir / f"{audio_id}.wav"
        
        # Generate a 0.5s beep at 440Hz (A4 note)
        sample_rate = 16000
        duration_sec = 0.5
        frequency = 440.0
        num_samples = int(sample_rate * duration_sec)
        
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            amplitude = 0.3 * math.sin(2 * math.pi * frequency * t)
            # Apply fade in/out to avoid clicks
            envelope = min(i / 1000, (num_samples - i) / 1000, 1.0)
            value = int(amplitude * envelope * 32767)
            samples.append(value)
        
        # Write WAV file
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            for sample in samples:
                wav_file.writeframes(struct.pack('<h', sample))
        
        logger.info(f"Generated TTS stub audio: {output_path}")
        return output_path, duration_sec


class TTSService:
    """TTS orchestration service."""
    
    def __init__(self, provider: Optional[TTSProvider] = None):
        data_dir = Path("/data/tts")
        self.provider = provider or StubTTSProvider(data_dir)
    
    async def text_to_speech(
        self,
        text: str,
        voice_preset: Optional[str] = None,
    ) -> tuple[str, float]:
        """
        Convert text to speech.
        
        Returns: (audio_url, duration_sec)
        """
        voice = voice_preset or settings.tts_voice_preset
        audio_path, duration = await self.provider.synthesize(text, voice)
        
        # Return URL path relative to static mount
        audio_url = f"/static/tts/{audio_path.name}"
        return audio_url, duration


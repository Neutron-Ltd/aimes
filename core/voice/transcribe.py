"""Voice transcription via DashScope or mock mode."""

from __future__ import annotations

import asyncio

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    settings = get_settings()
    if settings.voice_mock:
        return (
            "Show total equipment yield on my production line for today"
        )

    if not settings.dashscope_api_key:
        return "Voice transcription unavailable — configure DASHSCOPE_API_KEY"

    def _call() -> str:
        try:
            import dashscope
            from dashscope.audio.asr import Recognition

            recognition = Recognition(
                model="paraformer-realtime-v2",
                format="wav" if filename.endswith(".wav") else "mp3",
                sample_rate=16000,
                callback=None,
            )
            result = recognition.call(audio_bytes, api_key=settings.dashscope_api_key)
            if hasattr(result, "output") and result.output:
                sentences = result.output.get("sentence", [])
                if sentences:
                    return " ".join(s.get("text", "") for s in sentences)
            return str(getattr(result, "output", result))
        except Exception as exc:
            logger.warning("DashScope transcription failed: %s", exc)
            return f"[transcription error: {exc}]"

    return await asyncio.to_thread(_call)

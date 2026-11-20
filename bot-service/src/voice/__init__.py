"""Voice package - STT/TTS interfaces and factory."""
from .stt import SpeechToText, MockSTT, FasterWhisperSTT, HuggingFaceSTT, get_stt_provider, transcribe_audio
from .tts import TextToSpeech, MockTTS, PiperTTS, HuggingFaceTTS, BrowserTTS, get_tts_provider, synthesize_speech

__all__ = [
    "SpeechToText",
    "MockSTT",
    "FasterWhisperSTT",
    "HuggingFaceSTT",
    "get_stt_provider",
    "transcribe_audio",
    "TextToSpeech",
    "MockTTS",
    "PiperTTS",
    "HuggingFaceTTS",
    "BrowserTTS",
    "get_tts_provider",
    "synthesize_speech",
]
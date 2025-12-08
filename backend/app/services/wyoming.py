"""Wyoming Protocol Client for Whisper (STT) and Piper (TTS)
Using the official wyoming package for correct protocol implementation.
"""
import asyncio
import io
import wave
from typing import Optional
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.tts import Synthesize
from wyoming.asr import Transcribe, Transcript
from wyoming.event import async_read_event, async_write_event
from wyoming.info import Describe, Info

from ..config import settings


class WhisperService:
    """Wyoming Whisper (STT) Service"""
    
    def __init__(self):
        self.host = settings.whisper_host
        self.port = settings.whisper_port
    
    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio to text"""
        reader, writer = await asyncio.open_connection(self.host, self.port)
        
        try:
            # Send audio-start event
            await async_write_event(
                AudioStart(rate=sample_rate, width=2, channels=1).event(),
                writer
            )
            
            # Send audio chunks
            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await async_write_event(
                    AudioChunk(audio=chunk, rate=sample_rate, width=2, channels=1).event(),
                    writer
                )
            
            # Send audio-stop
            await async_write_event(AudioStop().event(), writer)
            
            # Wait for transcript
            while True:
                event = await asyncio.wait_for(async_read_event(reader), timeout=30.0)
                if event is None:
                    break
                    
                if Transcript.is_type(event.type):
                    transcript = Transcript.from_event(event)
                    return transcript.text
        
        finally:
            writer.close()
            await writer.wait_closed()
        
        return ""


class PiperService:
    """Wyoming Piper (TTS) Service"""
    
    def __init__(self):
        self.host = settings.piper_host
        self.port = settings.piper_port
        self.default_voice = settings.default_voice
    
    async def synthesize(
        self, 
        text: str, 
        voice: Optional[str] = None,
        length_scale: float = 1.0,  # Speed: lower=faster, higher=slower
        noise_scale: float = 0.667,  # Variation: higher=more expressive
        noise_w: float = 0.333,  # Phoneme timing: higher=more natural
    ) -> bytes:
        """Synthesize text to audio (WAV format)
        
        Args:
            text: Text to synthesize
            voice: Voice model name
            length_scale: Speaking speed (0.5-2.0, default 1.0)
            noise_scale: Voice variation/expressiveness (0-1, default 0.667)
            noise_w: Phoneme duration variation (0-1, default 0.333)
        """
        voice = voice or self.default_voice
        
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10.0
        )
        
        try:
            # Send synthesize event with voice and speech parameters
            synthesize_event = Synthesize(text=text).event()
            synthesize_event.data["voice"] = {"name": voice}
            
            # Add speech synthesis parameters for more natural output
            # These are passed to Piper for voice tuning
            synthesize_event.data["length_scale"] = length_scale
            synthesize_event.data["noise_scale"] = noise_scale  
            synthesize_event.data["noise_w"] = noise_w
            
            await async_write_event(synthesize_event, writer)
            
            # Collect audio chunks
            audio_chunks = []
            sample_rate = 22050
            sample_width = 2
            channels = 1
            
            while True:
                try:
                    event = await asyncio.wait_for(
                        async_read_event(reader),
                        timeout=60.0
                    )
                except asyncio.TimeoutError:
                    raise Exception("Timeout waiting for Piper response")
                
                if event is None:
                    break
                
                if AudioStart.is_type(event.type):
                    audio_start = AudioStart.from_event(event)
                    sample_rate = audio_start.rate
                    sample_width = audio_start.width
                    channels = audio_start.channels
                
                elif AudioChunk.is_type(event.type):
                    audio_chunk = AudioChunk.from_event(event)
                    audio_chunks.append(audio_chunk.audio)
                
                elif AudioStop.is_type(event.type):
                    break
            
            if not audio_chunks:
                raise Exception("No audio received from Piper")
            
            # Combine chunks and create WAV
            raw_audio = b"".join(audio_chunks)
            return self._create_wav(raw_audio, sample_rate, sample_width, channels)
        
        finally:
            writer.close()
            await writer.wait_closed()
    
    def _create_wav(self, audio_data: bytes, sample_rate: int, sample_width: int, channels: int) -> bytes:
        """Create WAV file from raw audio data"""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)
        return buffer.getvalue()
    
    async def get_info(self) -> Optional[Info]:
        """Get server info including available voices"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            
            try:
                await async_write_event(Describe().event(), writer)
                
                event = await asyncio.wait_for(
                    async_read_event(reader),
                    timeout=5.0
                )
                
                if event and Info.is_type(event.type):
                    return Info.from_event(event)
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            print(f"Failed to get Piper info: {e}")
        
        return None
    
    async def list_voices(self) -> list[dict]:
        """List available voices"""
        # Try to get voices from server
        try:
            info = await self.get_info()
            if info and info.tts:
                voices = []
                for tts_program in info.tts:
                    for voice in tts_program.voices or []:
                        # Handle language which might be a string or object
                        lang = "en"
                        if voice.languages:
                            first_lang = voice.languages[0]
                            if hasattr(first_lang, 'code'):
                                lang = first_lang.code
                            elif isinstance(first_lang, str):
                                lang = first_lang
                        
                        voices.append({
                            "id": voice.name,
                            "name": voice.name.replace("-", " ").replace("_", " ").title(),
                            "language": lang,
                            "quality": "medium",
                            "gender": "female"
                        })
                if voices:
                    return voices
        except Exception as e:
            print(f"Error getting voices from Piper: {e}")
        
        # Fallback to static list
        return [
            {"id": "en_US-lessac-medium", "name": "Lessac (US)", "language": "en_US", "quality": "medium", "gender": "female"},
            {"id": "en_US-lessac-high", "name": "Lessac High (US)", "language": "en_US", "quality": "high", "gender": "female"},
            {"id": "en_US-amy-medium", "name": "Amy (US)", "language": "en_US", "quality": "medium", "gender": "female"},
            {"id": "en_US-amy-low", "name": "Amy Low (US)", "language": "en_US", "quality": "low", "gender": "female"},
            {"id": "en_US-ljspeech-medium", "name": "LJSpeech (US)", "language": "en_US", "quality": "medium", "gender": "female"},
            {"id": "en_US-ljspeech-high", "name": "LJSpeech High (US)", "language": "en_US", "quality": "high", "gender": "female"},
            {"id": "en_US-kristin-medium", "name": "Kristin (US)", "language": "en_US", "quality": "medium", "gender": "female"},
            {"id": "en_GB-alba-medium", "name": "Alba (GB Scottish)", "language": "en_GB", "quality": "medium", "gender": "female"},
            {"id": "en_GB-jenny_dioco-medium", "name": "Jenny (GB)", "language": "en_GB", "quality": "medium", "gender": "female"},
            {"id": "en_GB-cori-medium", "name": "Cori (GB Welsh)", "language": "en_GB", "quality": "medium", "gender": "female"},
            {"id": "en_GB-semaine-medium", "name": "Semaine (GB)", "language": "en_GB", "quality": "medium", "gender": "female"},
        ]


# Singleton instances
whisper_service = WhisperService()
piper_service = PiperService()

"""Audio processing utilities for Galatea.

Functions for cleaning text for TTS, audio encoding/decoding, etc.
"""
import re
from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)


def clean_for_speech(text: str) -> str:
    """Remove emojis, action markers, thinking tags, and formatting from text for natural TTS.
    
    This prevents the TTS from saying things like "smiling face with smiling eyes"
    or reading out "*smiles warmly*" literally, or speaking <think> blocks.
    
    Args:
        text: Raw text from LLM response
        
    Returns:
        Cleaned text suitable for TTS synthesis
    """
    # Remove <think>...</think> blocks (thinking model output)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining unclosed think tags
    text = re.sub(r'</?think(?:ing)?>', '', text, flags=re.IGNORECASE)
    
    # Pattern to match emojis and other symbols that shouldn't be spoken
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "\U00002600-\U000026FF"  # misc symbols
        "\U00002700-\U000027BF"  # dingbats
        "\U0001F000-\U0001F02F"  # mahjong tiles
        "\U0001F0A0-\U0001F0FF"  # playing cards
        "]+", 
        flags=re.UNICODE
    )
    
    # Remove emojis
    text = emoji_pattern.sub('', text)
    
    # Remove action markers like *smiles*, *laughs*, *nods*
    text = re.sub(r'\*[^*]+\*', '', text)
    
    # Remove parenthetical actions like (smiles) (laughs warmly)
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Remove bracketed actions like [smiling] [nodding]
    text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Remove common text emoticons
    text = re.sub(r'[:;]-?[)(\[\]DPp]', '', text)  # :) :( ;) :D etc
    text = re.sub(r'<3', '', text)  # heart
    
    # Remove markdown formatting but keep the text
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code` -> code
    
    # Clean up extra whitespace and punctuation artifacts
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.,!?])\s*([.,!?])', r'\1', text)  # Remove double punctuation
    text = text.strip()
    
    return text


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for streaming TTS.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def detect_sentence_boundary(buffer: str) -> tuple[Optional[str], str]:
    """Check if buffer contains a complete sentence.
    
    Args:
        buffer: Text buffer being accumulated
        
    Returns:
        (complete_sentence, remaining_buffer) or (None, buffer) if no complete sentence
    """
    # Look for sentence endings: . ! ? followed by space or end
    match = re.search(r'[.!?](?:\s|$)', buffer)
    
    if match:
        end_pos = match.end()
        sentence = buffer[:end_pos].strip()
        remainder = buffer[end_pos:].strip()
        
        # Only return if sentence is substantial
        if sentence and len(sentence) > 3:
            return sentence, remainder
    
    return None, buffer


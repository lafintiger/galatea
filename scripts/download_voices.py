#!/usr/bin/env python3
"""
Download Piper TTS voices (Female EN-US and EN-GB)
This script downloads voice models to the Piper Docker container's volume.
"""

import os
import sys
import requests
from pathlib import Path
import tarfile
import shutil

# Piper voice repository
PIPER_VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# Female voices to download
VOICES = [
    # US English - Female
    {"name": "en_US-amy-low", "quality": "low"},
    {"name": "en_US-amy-medium", "quality": "medium"},
    {"name": "en_US-lessac-low", "quality": "low"},
    {"name": "en_US-lessac-medium", "quality": "medium"},
    {"name": "en_US-lessac-high", "quality": "high"},
    {"name": "en_US-ljspeech-low", "quality": "low"},
    {"name": "en_US-ljspeech-medium", "quality": "medium"},
    {"name": "en_US-ljspeech-high", "quality": "high"},
    {"name": "en_US-kristin-medium", "quality": "medium"},
    
    # GB English - Female
    {"name": "en_GB-alba-medium", "quality": "medium"},
    {"name": "en_GB-jenny_dioco-medium", "quality": "medium"},
    {"name": "en_GB-cori-medium", "quality": "medium"},
    {"name": "en_GB-semaine-medium", "quality": "medium"},
]

def get_voice_url(voice_name: str) -> tuple[str, str]:
    """Get the download URLs for a voice's onnx and json files"""
    # Parse voice name: en_US-amy-low -> en/en_US/amy/low
    parts = voice_name.split("-")
    lang_region = parts[0]  # en_US
    lang = lang_region.split("_")[0]  # en
    speaker = parts[1]  # amy
    quality = parts[2]  # low
    
    base_path = f"{lang}/{lang_region}/{speaker}/{quality}"
    onnx_url = f"{PIPER_VOICES_URL}/{base_path}/{voice_name}.onnx"
    json_url = f"{PIPER_VOICES_URL}/{base_path}/{voice_name}.onnx.json"
    
    return onnx_url, json_url


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with progress indicator"""
    try:
        print(f"  Downloading: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size:
                    percent = (downloaded / total_size) * 100
                    print(f"\r  Progress: {percent:.1f}%", end="", flush=True)
        
        print()  # New line after progress
        return True
        
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def main():
    # Default output directory (can be overridden)
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./voices")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Piper Voice Downloader")
    print("Downloading female EN-US and EN-GB voices")
    print("=" * 60)
    print(f"\nOutput directory: {output_dir.absolute()}")
    print(f"Voices to download: {len(VOICES)}")
    print()
    
    successful = 0
    failed = 0
    
    for voice in VOICES:
        voice_name = voice["name"]
        print(f"\n📥 Downloading: {voice_name}")
        
        onnx_url, json_url = get_voice_url(voice_name)
        
        onnx_path = output_dir / f"{voice_name}.onnx"
        json_path = output_dir / f"{voice_name}.onnx.json"
        
        # Skip if already downloaded
        if onnx_path.exists() and json_path.exists():
            print(f"  ✓ Already exists, skipping")
            successful += 1
            continue
        
        # Download ONNX model
        if download_file(onnx_url, onnx_path):
            # Download JSON config
            if download_file(json_url, json_path):
                print(f"  ✓ Downloaded successfully")
                successful += 1
            else:
                onnx_path.unlink(missing_ok=True)
                failed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Download complete!")
    print(f"  ✓ Successful: {successful}")
    print(f"  ✗ Failed: {failed}")
    print("=" * 60)
    
    if output_dir != Path("./voices"):
        print(f"\nVoices downloaded to: {output_dir}")
    else:
        print("\nTo use with Docker Piper, copy these files to your Piper volume:")
        print("  docker cp voices/. piper:/data/")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())





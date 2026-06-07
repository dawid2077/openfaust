import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from functools import cache  



#!this file was vibecoded 
@cache
def get_companion_identity(personality_path: Path) -> str:
    """
    Reads a raw personality profile text file from a Path object, uses a fast, 
    deterministic LLM call to extract the companion's name, and returns it.
    
    Falls back gracefully to 'Faust' if the file is missing or the API fails.
    """
    load_dotenv()
    
    # 1. Safely resolve and read the user's raw text file
    try:
        if not isinstance(personality_path, Path):
            personality_path = Path(personality_path)
            
        if not personality_path.exists():
            print(f"⚠️  Warning: Profile not found at {personality_path}. Defaulting name to 'Faust'.")
            return "Faust"
            
        raw_profile = personality_path.read_text(encoding="utf-8").strip()
        
        # Guard against completely empty files
        if not raw_profile:
            print(f"⚠️  Warning: {personality_path} is empty. Defaulting name to 'Faust'.")
            return "Faust"
            
    except Exception as e:
        print(f"❌ Error reading file at {personality_path}: {e}. Defaulting to 'Faust'.")
        return "Faust"

    # 2. Fire a single targeted, low-latency extraction request via OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    
    system_instruction = (
        "You are a precise data extraction utility. Read the provided AI companion personality profile text.\n\n"
        "Identify the primary name or moniker the assistant goes by or is assigned. "
        "If no specific name is mentioned anywhere in the text, you must return 'Faust'.\n\n"
        "Output ONLY a valid JSON object matching this schema: {\"name\": \"extracted_name_here\"}."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Profile Text:\n{raw_profile}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0  # Absolute determinism for reliable JSON outputs
        )
        
        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        extracted_name = data.get("name", "Faust").strip()
        
        print(f"⚙️  Identity Extractor: Resolved active companion name -> [{extracted_name}]")
        return extracted_name

    except Exception as e:
        print(f"❌ Failed to extract name via API: {e}. Falling back to 'Faust'.")
        return "Faust"


# Example local test run when executing the file directly
if __name__ == "__main__":
    # Mirroring your environment path configuration setup
    default_path = Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))
    
    print("--- Executing Local Extraction Test ---")
    companion_name = get_companion_identity(default_path)
    print(f"Resulting Companion Name: {companion_name}")
import os
from pathlib import Path

# --- 1. SETTINGS (Edit these directly here) ---
# We removed pydantic-settings. You can just change these values here.
MODEL_NAME = "qwen2.5:7b-instruct"
API_HOST = "0.0.0.0"
API_PORT = 8001

ALLOWED_ORIGINS = [
    "http://localhost:3000",       # Common React/Vue dev port
    "http://localhost:8080",       # Common HTML dev port
]

# --- 2. GLOBAL SAFETY RULES ---
BASE_RULES_EN = """
Follow these rules STRICTLY:
1. **NEVER Give Medical Advice:** Do not diagnose, treat, or prescribe.
2. **Redirect Medical Questions:** Gently decline and remind them to speak with a doctor.
3. **Be Empathetic:** Validate the user's feelings.
4. **Keep it Simple:** Avoid excessive medical jargon.
5. **Safety First:** If self-harm is mentioned, advise them to seek emergency help immediately.
"""

BASE_RULES_RO = """
Urmează aceste reguli cu STRICTEȚE:
1. **NU oferi sfaturi medicale:** Nu diagnostica, nu trata și nu prescrie medicamente.
2. **Redirecționează întrebările medicale:** Refuză politicos și reamintește-le să discute cu medicul lor.
3. **Fii empatic:** Validează sentimentele utilizatorului.
4. **Păstrează limbajul simplu:** Evită termenii medicali complicați.
5. **Siguranța pe primul loc:** Dacă utilizatorul menționează auto-vătămarea, sfătuiește-l imediat să caute ajutor de urgență.
"""

# --- 3. DYNAMIC PROMPT LOADING ---
def get_full_prompt(lang: str, filename: str) -> str:
    """
    Reads the specific persona text file and appends the safety rules.
    """
    base_dir = Path(__file__).parent
    file_path = base_dir / "prompts" / lang / filename
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            persona_text = f.read().strip()
    except FileNotFoundError:
        # Fallback if you haven't run the setup script yet
        print(f"WARNING: Missing prompt file {file_path}")
        persona_text = "You are a helpful assistant."

    # Combine text with the correct language rules
    rules = BASE_RULES_RO if lang == "ro" else BASE_RULES_EN
    return f"{persona_text}\n\n{rules}"

# --- 4. SYSTEM PROMPTS DICTIONARY ---
SYSTEM_PROMPTS = {
    "en": {
        "ms": {
            "patient": get_full_prompt("en", "ms_patient.txt"),
            "carer":   get_full_prompt("en", "ms_carer.txt")
        },
        "parkinsons": {
            "patient": get_full_prompt("en", "parkinsons_patient.txt"),
            "carer":   get_full_prompt("en", "parkinsons_carer.txt")
        },
        "alzheimers": {
            "patient": get_full_prompt("en", "alzheimers_patient.txt"),
            "carer":   get_full_prompt("en", "alzheimers_carer.txt")
        }
    },
    "ro": {
        "ms": {
            "patient": get_full_prompt("ro", "ms_patient.txt"),
            "carer":   get_full_prompt("ro", "ms_carer.txt")
        },
        "parkinsons": {
            "patient": get_full_prompt("ro", "parkinsons_patient.txt"),
            "carer":   get_full_prompt("ro", "parkinsons_carer.txt")
        },
        "alzheimers": {
            "patient": get_full_prompt("ro", "alzheimers_patient.txt"),
            "carer":   get_full_prompt("ro", "alzheimers_carer.txt")
        }
    }
}
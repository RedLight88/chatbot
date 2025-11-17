import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import config
from typing import List

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    disease: str
    role: str
    language: str  # <--- NEW: We need to know the language

@app.post("/chat")
def generate_response(request: ChatRequest):
    try:
        # 1. Normalize inputs
        lang_key = request.language.lower()
        disease_key = request.disease.lower()
        role_key = request.role.lower()

        # 2. Validation
        if lang_key not in config.SYSTEM_PROMPTS:
             # Fallback to English if language not found, or raise error
             lang_key = "en" 

        if disease_key not in config.SYSTEM_PROMPTS[lang_key]:
            raise HTTPException(status_code=400, detail="Invalid disease")
            
        if role_key not in config.SYSTEM_PROMPTS[lang_key][disease_key]:
             raise HTTPException(status_code=400, detail="Invalid role")
            
        # 3. Get Prompt
        system_prompt = config.SYSTEM_PROMPTS[lang_key][disease_key][role_key]

        # 4. Prepare for Ollama
        messages_to_send = [{'role': 'system', 'content': system_prompt}]
        messages_to_send.extend([msg.model_dump() for msg in request.messages])

        print(f"--- Chat: {lang_key.upper()} | {disease_key} | {role_key} ---")
        
        response = ollama.chat(model=config.MODEL_NAME, messages=messages_to_send)
        return response['message']

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
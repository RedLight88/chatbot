import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import config
import re
from typing import List

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    disease: str
    role: str
    language: str

class SummaryResponse(BaseModel):
    symptoms: List[str]
    recommendations: List[str]

@app.post("/chat")
def generate_response(request: ChatRequest):
    try:
        lang_key = request.language.lower()
        disease_key = request.disease.lower()
        role_key = request.role.lower()

        if lang_key not in config.SYSTEM_PROMPTS:
             lang_key = "en" 

        if disease_key not in config.SYSTEM_PROMPTS[lang_key]:
            raise HTTPException(status_code=400, detail="Invalid disease")
            
        if role_key not in config.SYSTEM_PROMPTS[lang_key][disease_key]:
             raise HTTPException(status_code=400, detail="Invalid role")
            
        system_prompt = config.SYSTEM_PROMPTS[lang_key][disease_key][role_key]

        messages_to_send = [{'role': 'system', 'content': system_prompt}]
        messages_to_send.extend([msg.model_dump() for msg in request.messages])

        print(f"--- Chat: {lang_key.upper()} | {disease_key} | {role_key} ---")
        
        response = ollama.chat(model=config.MODEL_NAME, messages=messages_to_send)
        return response['message']

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summary", response_model=SummaryResponse)
def generate_summary(request: ChatRequest):
    try:
        # 1. Determine Language
        lang_key = request.language.lower()
        if lang_key not in config.SUMMARY_PROMPTS:
            lang_key = "en"

        system_instruction = config.SUMMARY_PROMPTS[lang_key]

        # 2. Format the Django Message History into a Text Block
        conversation_text = ""
        for msg in request.messages:
            # We map 'user'/'assistant' to clear labels for the LLM
            role_label = "User" if msg.role == "user" else "AI"
            conversation_text += f"{role_label}: {msg.content}\n"

        # 3. Construct the Prompt
        # We send the instruction + the conversation log
        final_prompt = f"{system_instruction}\n\nCONVERSATION LOG:\n{conversation_text}"
        
        messages_to_send = [{'role': 'user', 'content': final_prompt}]

        print(f"--- Summary Request: {lang_key.upper()} ---")

        # 4. Get LLM Response (Raw Text)
        response = ollama.chat(model=config.MODEL_NAME, messages=messages_to_send)
        raw_text = response['message']['content']
        
        print(f"--- Raw LLM Output ---\n{raw_text}\n----------------------")

        # 5. Parse the Text Output (Python Logic)
        symptoms_list = []
        recommendations_list = []
        
        # Normalize newlines just in case
        raw_text = raw_text.replace("\r\n", "\n")
        
        current_section = None
        lines = raw_text.split('\n')
        
        for line in lines:
            stripped_line = line.strip()
            
            # A. Detect Headers
            if "[SYMPTOMS]" in stripped_line.upper():
                current_section = "symptoms"
                continue
            elif "[RECOMMENDATIONS]" in stripped_line.upper():
                current_section = "recommendations"
                continue
            
            # B. Skip empty lines
            if not stripped_line:
                continue
                
            # C. Extract Content if inside a section
            if current_section:
                # Regex to remove bullet points like "-", "*", "1.", "•"
                # ^ start of line, [\-\*\•\d\.]+ matches bullet chars, \s+ matches space
                clean_item = re.sub(r'^[\-\*\•\d\.]+\s+', '', stripped_line)
                
                if clean_item:
                    if current_section == "symptoms":
                        symptoms_list.append(clean_item)
                    elif current_section == "recommendations":
                        recommendations_list.append(clean_item)

        # 6. Return formatted JSON
        result = {
            "symptoms": symptoms_list,
            "recommendations": recommendations_list
        }
        
        return result

    except Exception as e:
        print(f"Error in /summary: {e}")
        # On error, return empty lists so the frontend doesn't crash
        return {"symptoms": [], "recommendations": []}

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
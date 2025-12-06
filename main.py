import uvicorn
import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import List, Literal, Annotated
import ollama
import config

# --- 1. SETUP LOGGING ---
# This configures the logs to show timestamps and severity (INFO/ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("medical_ai")

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # 1. SECURITY: Only allow specific domains from config
    allow_origins=config.ALLOWED_ORIGINS,
    
    # 2. CREDENTIALS: Set to True if your frontend sends Cookies or Authorization headers
    allow_credentials=True,
    
    # 3. METHODS: Only allow the methods your API actually uses
    # "OPTIONS" is mandatory for CORS pre-flight checks.
    allow_methods=["GET", "POST", "OPTIONS"], 
    
    # 4. HEADERS: Usually safe to keep as "*", or restrict to ["Content-Type", "Authorization"]
    allow_headers=["*"],
)

# --- 2. DEPENDENCY INJECTION ---
async def get_ai_client():
    """
    Creates and returns an async Ollama client.
    Injecting this allows us to easily mock it during testing.
    """
    return ollama.AsyncClient()

# This 'Annotated' alias makes our endpoint signatures cleaner below
AIClient = Annotated[ollama.AsyncClient, Depends(get_ai_client)]

# --- 3. DATA MODELS ---

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    disease: Literal["ms", "parkinsons", "alzheimers"]
    role: Literal["patient", "carer"]
    language: Literal["en", "ro"]

    # Normalize inputs (e.g. "MS " -> "ms") automatically
    @field_validator('disease', 'role', 'language', mode='before')
    @classmethod
    def normalize_inputs(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

class SummaryResponse(BaseModel):
    symptoms: List[str]
    recommendations: List[str]

# --- 4. ENDPOINTS ---

@app.post("/chat", response_model=Message)
async def generate_response(request: ChatRequest, client: AIClient):
    """
    Generates a conversational response based on the persona in config.
    """
    try:
        # Retrieve the specific system prompt from our config dictionary
        system_prompt = config.SYSTEM_PROMPTS[request.language][request.disease][request.role]
        
        # Prepare the message history
        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend([m.model_dump() for m in request.messages])

        logger.info(f"Chat Request: {request.disease} | {request.role} ({request.language})")

        # Call Ollama using the injected client
        response = await client.chat(model=config.MODEL_NAME, messages=messages)
        
        return response['message']

    except Exception as e:
        logger.error(f"Chat Failed: {e}")
        raise HTTPException(status_code=500, detail="Error generating response")


@app.post("/summary", response_model=SummaryResponse)
async def generate_summary(request: ChatRequest, client: AIClient):
    """
    Summarizes conversation into JSON symptoms and recommendations.
    """
    try:
        logger.info(f"Summary Request: {request.language}")

        # 1. Select Language for Instructions
        if request.language == 'ro':
            base_instruction = (
                "Analizează conversația. Returnează un obiect JSON cu două chei: "
                "'symptoms' (listă de șiruri) și 'recommendations' (listă de șiruri)."
            )
        else:
            base_instruction = (
                "Analyze the conversation. Return a JSON object with two keys: "
                "'symptoms' (list of strings) and 'recommendations' (list of strings)."
            )

        # 2. Format the Conversation Log
        conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        final_prompt = f"{base_instruction}\n\nLOG:\n{conversation_text}"

        # 3. Call Ollama with JSON enforcement
        # We use the injected 'client' here too
        response = await client.chat(
            model=config.MODEL_NAME, 
            messages=[{'role': 'user', 'content': final_prompt}],
            format=SummaryResponse.model_json_schema() # Forces strict JSON structure
        )

        # 4. Parse the result
        raw_content = response['message']['content']
        # Validate that the AI actually gave us the correct JSON structure
        parsed_data = SummaryResponse.model_validate_json(raw_content)
        
        return parsed_data

    except Exception as e:
        logger.error(f"Summary Failed: {e}")
        # Return empty structure so the frontend doesn't crash
        return SummaryResponse(symptoms=[], recommendations=[])

# --- 5. SERVER RUNNER ---
if __name__ == "__main__":
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
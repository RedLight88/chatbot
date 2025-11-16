import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field  # <-- Import Field
import ollama
import config
from typing import List, Dict, Any   # <-- Import List, Dict, Any

app = FastAPI(
    title="AI Support Bot API",
    description="A secure, stateless bridge between a web client and the Ollama model."
)

# --- NEW DATA SHAPES ---

# 1. Define the shape of a single message object
# (This matches Ollama's format)
class Message(BaseModel):
    role: str
    content: str

# 2. Define the "Data Shape" for incoming requests
class ChatRequest(BaseModel):
    # We now expect the full conversation history
    messages: List[Message]
    
    # We still need the disease to pick the system prompt
    disease: str

# --------------------------


# 3. Create the main chat endpoint
@app.post("/chat")
def generate_response(request: ChatRequest):
    """
    This is the main function that gets called by Django.
    
    Django is responsible for:
    1. Storing the chat history.
    2. Getting the 'disease' for the conversation.
    3. Sending the *full message history* and 'disease' here.
    
    This function adds the correct system prompt and gets the
    next message from the LLM.
    """
    try:
        # 1. Get the correct system prompt from config
        disease_key = request.disease.lower()
        system_prompt = config.SYSTEM_PROMPTS.get(disease_key)

        if not system_prompt:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid 'disease' key. Must be one of: {list(config.SYSTEM_PROMPTS.keys())}"
            )

        # 2. Prepare the messages for Ollama
        # We create a *new* list, starting with the system prompt,
        # and then extending it with the history from the request.
        
        # We must convert our Pydantic models back to plain dicts
        # for the ollama library.
        messages_from_django = [msg.model_dump() for msg in request.messages]

        messages_to_send = [
            {
                'role': 'system',
                'content': system_prompt
            }
        ]
        
        # Add the entire conversation history after the system prompt
        messages_to_send.extend(messages_from_django)

        # 3. Call the Ollama service
        print(f"--- Sending request to Ollama (Context: {disease_key}, History: {len(messages_to_send)} messages)... ---")
        response = ollama.chat(
            model=config.MODEL_NAME, 
            messages=messages_to_send
        )
        print("--- Received response from Ollama. ---")

        # 4. Extract just the new AI message
        # This is already in the { 'role': '...', 'content': '...' }
        # format, so we can send it directly back to Django.
        bot_reply = response['message']

        # 5. Send the clean reply (as a dict) back to Django
        # Django will then save this to its database.
        return bot_reply

    except Exception as e:
        print(f"Error calling Ollama: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

# 4. Add a "health check" endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "model_ready": config.MODEL_NAME}


# 5. This makes the server runnable with "python main.py"
if __name__ == "__main__":
    print(f"--- Starting AI Service on http://{config.API_HOST}:{config.API_PORT} ---")
    print(f"--- Using model: {config.MODEL_NAME} ---")
    
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )
# Import the ASGI server to run the application
import uvicorn
# Import FastAPI framework and HTTP exception handler for error reporting
from fastapi import FastAPI, HTTPException
# Import BaseModel for data validation and type checking
from pydantic import BaseModel
# Import the Python client for interacting with the Ollama LLM
import ollama
# Import a local configuration file containing API keys, prompts, and settings
import config
# Import the regex module for text pattern matching (used in parsing summaries)
import re
# Import List for type hinting in Pydantic models
from typing import List

# Initialize the FastAPI application instance
app = FastAPI()

# --- DATA MODELS ---

# Defines the structure of a single chat message
class Message(BaseModel):
    role: str       # Who sent the message (e.g., 'user', 'assistant', 'system')
    content: str    # The actual text body of the message

# Defines the structure of the incoming request for Chat and Summary
class ChatRequest(BaseModel):
    messages: List[Message] # The full history of the conversation so far
    disease: str            # Context: The specific condition being discussed
    role: str               # Context: The persona the AI should adopt
    language: str           # Context: The language code 

# Defines the structure of the response for the /summary endpoint
class SummaryResponse(BaseModel):
    symptoms: List[str]         # A list of extracted symptoms
    recommendations: List[str]  # A list of extracted advice/recommendations

# --- ENDPOINTS ---

# Route to handle conversational chat requests
@app.post("/chat", response_model=Message)
def generate_response(request: ChatRequest):
    try:
        # Normalize input strings to lowercase to match keys in the config dictionary
        lang_key = request.language.lower()
        disease_key = request.disease.lower()
        role_key = request.role.lower()

        # Check if the requested language exists in config; default to English if not
        if lang_key not in config.SYSTEM_PROMPTS:
             lang_key = "en" 

        # Validate if the specific disease exists under that language in config
        if disease_key not in config.SYSTEM_PROMPTS[lang_key]:
            # Return a 400 Bad Request error if the disease is not supported
            raise HTTPException(status_code=400, detail="Invalid disease")
            
        # Validate if the specific role exists for that disease
        if role_key not in config.SYSTEM_PROMPTS[lang_key][disease_key]:
             # Return a 400 Bad Request error if the role is not supported
             raise HTTPException(status_code=400, detail="Invalid role")
            
        # Retrieve the specific system instruction (prompt) from the nested config dict
        system_prompt = config.SYSTEM_PROMPTS[lang_key][disease_key][role_key]

        # Initialize the message list with the System Prompt (instructions for the AI)
        messages_to_send = [{'role': 'system', 'content': system_prompt}]
        
        # Append the user's conversation history, converting Pydantic models to dicts
        messages_to_send.extend([msg.model_dump() for msg in request.messages])

        # Log the chat context to the server console for debugging
        print(f"--- Chat: {lang_key.upper()} | {disease_key} | {role_key} ---")
        
        # Send the complete message history to Ollama to generate the next response
        response = ollama.chat(model=config.MODEL_NAME, messages=messages_to_send)
        
        # Return the 'message' part of the Ollama response (contains role and content)
        return response['message']

    # Catch any unexpected errors during the process
    except Exception as e:
        print(f"Error: {e}")
        # Return a 500 Internal Server Error with the exception details
        raise HTTPException(status_code=500, detail=str(e))

# Route to summarize the conversation into structured data
@app.post("/summary", response_model=SummaryResponse)
def generate_summary(request: ChatRequest):
    try:
        # 1. Determine Language for the summary instructions
        lang_key = request.language.lower()
        # Fallback to English if the language isn't in the summary config
        if lang_key not in config.SUMMARY_PROMPTS:
            lang_key = "en"

        # Retrieve the instruction that tells the AI how to format the summary
        system_instruction = config.SUMMARY_PROMPTS[lang_key]

        # 2. Format the Message History into a single Text Block
        conversation_text = ""
        # Loop through every message in the request history
        for msg in request.messages:
            # Map technical role names ('user'/'assistant') to readable labels ('User'/'AI')
            role_label = "User" if msg.role == "user" else "AI"
            # Append the labeled message to the transcript string
            conversation_text += f"{role_label}: {msg.content}\n"

        # 3. Construct the Final Prompt
        # Combine the instructions with the formatted conversation transcript
        final_prompt = f"{system_instruction}\n\nCONVERSATION LOG:\n{conversation_text}"
        
        # Prepare the message payload for Ollama (Single-shot prompt)
        messages_to_send = [{'role': 'user', 'content': final_prompt}]

        # Log the summary request
        print(f"--- Summary Request: {lang_key.upper()} ---")

        # 4. Get LLM Response (Raw Text)
        # Call Ollama to generate the summary text
        response = ollama.chat(model=config.MODEL_NAME, messages=messages_to_send)
        # Extract the raw content string from the response
        raw_text = response['message']['content']
        
        # Log the raw output for debugging logic issues
        print(f"--- Raw LLM Output ---\n{raw_text}\n----------------------")

        # 5. Parse the Text Output (Python Logic)
        # Initialize empty lists to hold the parsed data
        symptoms_list = []
        recommendations_list = []
        
        # Normalize newlines to handle Windows (\r\n) vs Unix (\n) formatting
        raw_text = raw_text.replace("\r\n", "\n")
        
        # Variable to track which section of the summary we are currently reading
        current_section = None
        # Split the raw text into individual lines
        lines = raw_text.split('\n')
        
        # Iterate over each line to parse content
        for line in lines:
            # Remove leading/trailing whitespace
            stripped_line = line.strip()
            
            # A. Detect Headers
            # Check if this line marks the start of the Symptoms section
            if "[SYMPTOMS]" in stripped_line.upper():
                current_section = "symptoms"
                continue # Skip to the next line
            # Check if this line marks the start of the Recommendations section
            elif "[RECOMMENDATIONS]" in stripped_line.upper():
                current_section = "recommendations"
                continue # Skip to the next line
            
            # B. Skip empty lines to avoid adding blanks to the lists
            if not stripped_line:
                continue
                
            # C. Extract Content if we are currently inside a recognized section
            if current_section:
                # Regex Explanation:
                # ^ matches start of line
                # [\-\*\•\d\.]+ matches hyphens, asterisks, dots, digits (bullet points)
                # \s+ matches following whitespace
                # This removes things like "1. ", "- ", or "* " from the start of the line
                clean_item = re.sub(r'^[\-\*\•\d\.]+\s+', '', stripped_line)
                
                # If there is text left after cleaning
                if clean_item:
                    # Add to the appropriate list based on the current section
                    if current_section == "symptoms":
                        symptoms_list.append(clean_item)
                    elif current_section == "recommendations":
                        recommendations_list.append(clean_item)

        # 6. Return formatted JSON
        # Construct the dictionary that matches the SummaryResponse Pydantic model
        result = {
            "symptoms": symptoms_list,
            "recommendations": recommendations_list
        }
        
        # Return the result; FastAPI converts this dict to JSON automatically
        return result

    # Error handling for the summary endpoint
    except Exception as e:
        print(f"Error in /summary: {e}")
        # Return empty lists to prevent the frontend application from crashing
        return {"symptoms": [], "recommendations": []}

# Standard boilerplate to run the app directly
if __name__ == "__main__":
    # Start the Uvicorn server using settings from the config file
    # reload=True allows the server to auto-restart when code changes
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
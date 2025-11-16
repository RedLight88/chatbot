import requests
import json

# --- Settings ---
API_URL = "http://127.0.0.1:8001/chat"
# -----------------

def main():
    print("--- AI Bot Test Client ---")
    print("Which bot persona do you want to test?")
    print("1: Multiple Sclerosis (ms)")
    print("2: Parkinson's (parkinsons)")
    print("3: Alzheimer's (alzheimers)")
    
    disease_key = ""
    while not disease_key:
        choice = input("Enter number (1, 2, or 3): ")
        if choice == '1':
            disease_key = 'ms'
        elif choice == '2':
            disease_key = 'parkinsons'
        elif choice == '3':
            disease_key = 'alzheimers'
        else:
            print("Invalid choice. Please try again.")
            
    print(f"\nTesting bot: '{disease_key}'. Type 'exit' or 'quit' to end.")
    print("-" * 30)

    # This list will store our entire conversation
    message_history = []

    while True:
        # 1. Get user input
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("--- Exiting test client. ---")
            break
        
        # 2. Add the new user message to our history
        message_history.append({
            "role": "user",
            "content": user_input
        })
        
        # 3. Build the request payload
        #    This matches the ChatRequest model in main.py
        payload = {
            "messages": message_history,  # Send the FULL history
            "disease": disease_key
        }
        
        try:
            # 4. Send the request to the FastAPI server
            response = requests.post(API_URL, json=payload)
            
            # Check for HTTP errors (like 400 or 500)
            response.raise_for_status()
            
            # 5. Get the bot's reply from the JSON response
            bot_reply = response.json()  # This will be a dict
            
            # 6. Print the bot's content
            print(f"Bot: {bot_reply.get('content')}")
            
            # 7. Add the bot's reply to our history for context
            message_history.append(bot_reply)

        except requests.exceptions.ConnectionError:
            print("\n--- ERROR ---")
            print(f"Could not connect to {API_URL}.")
            print("Is your 'python main.py' server running in another terminal?")
            print("---------------")
            break
        except requests.exceptions.RequestException as e:
            print(f"\n--- An Error Occurred ---")
            print(f"Error: {e}")
            print(f"Response Body: {response.text}")
            print("---------------------------")


if __name__ == "__main__":
    main()
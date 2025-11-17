import requests

API_URL = "http://127.0.0.1:8001/chat"

# --- TRANSLATIONS FOR THE CLIENT UI ---
UI_STRINGS = {
    "en": {
        "ask_role": "Which bot persona?\n1: Patient\n2: Carer\nChoice: ",
        "ask_disease": "Which disease?\n1: MS\n2: Parkinson's\n3: Alzheimer's\nChoice: ",
        "start": "--- Starting Chat. Type 'exit' to end ---",
        "you": "You: ",
        "bot": "Bot: ",
        "error": "Connection Error.",
        "exit": "Exiting..."
    },
    "ro": {
        "ask_role": "Ce rol doriți să testați?\n1: Pacient\n2: Îngrijitor (Carer)\nAlegere: ",
        "ask_disease": "Despre ce afecțiune este vorba?\n1: Scleroză Multiplă (MS)\n2: Parkinson\n3: Alzheimer\nAlegere: ",
        "start": "--- Începem conversația. Scrie 'exit' pentru a încheia ---",
        "you": "Tu: ",
        "bot": "Bot: ",
        "error": "Eroare de conexiune.",
        "exit": "Se închide..."
    }
}

def main():
    print("--- AI Bot Test Client ---")
    print("Select Language / Selectați Limba:")
    print("1: English")
    print("2: Română")
    
    # 1. Determine Language
    lang_choice = input("Choice (1/2): ")
    lang_key = "ro" if lang_choice == '2' else "en"
    
    # Get the UI dictionary for the selected language
    ui = UI_STRINGS[lang_key]

    # 2. Get Role
    role_key = ""
    while not role_key:
        choice = input(ui["ask_role"])
        if choice == '1': role_key = 'patient'
        elif choice == '2': role_key = 'carer'

    # 3. Get Disease
    disease_key = ""
    while not disease_key:
        choice = input(ui["ask_disease"])
        if choice == '1': disease_key = 'ms'
        elif choice == '2': disease_key = 'parkinsons'
        elif choice == '3': disease_key = 'alzheimers'

    print(f"\n{ui['start']}")
    
    message_history = []

    while True:
        user_input = input(ui["you"])
        
        if user_input.lower() in ['exit', 'quit', 'gata']:
            print(ui["exit"])
            break
        
        message_history.append({"role": "user", "content": user_input})
        
        payload = {
            "messages": message_history,
            "disease": disease_key,
            "role": role_key,
            "language": lang_key  # Send the language to the server!
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            bot_reply = response.json()
            
            print(f"{ui['bot']}{bot_reply.get('content')}")
            message_history.append(bot_reply)

        except Exception as e:
            print(f"{ui['error']} ({e})")
            break

if __name__ == "__main__":
    main()
# chatbot

Steps to run:
1.download https://ollama.com/  
2.open a terminal and do: ollama pull qwen2.5:7b-instruct  
3.make a virtual environment: python -m venv .venv  
4.activate the environment: .\.venv\Scripts\activate  
5.in the same terminal run: pip install fastapi "uvicorn[standard]" ollama pydantic requests  
6.run it: python main.py  
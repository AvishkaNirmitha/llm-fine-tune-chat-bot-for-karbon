import requests
import json

# Ollama API URL
OLLAMA_URL = "http://localhost:11434/api/generate"

# Bot's identity
BOT_NAME = "Spera"

# Initialize a session for persistent HTTP connection
session = requests.Session()
session.headers.update({"Connection": "keep-alive"})  # Enable Keep-Alive

# Function to process user input
def process_text(text):
    if not text.strip():
        return

    # Define request payload
    payload = {
        "model": "phi3:3.8b",
        "prompt": (
            f"You are an AI assistant named '{BOT_NAME}'. "
            "Meaning of 'spera' in Romanian is HOPE. "
            "You should Answer in short format.\n"
            f"User: {text}\n{BOT_NAME}:"
        ),
        "stream": True,
        "options": {"temperature": 0.5, "max_tokens": 20}  # Short responses
    }

    buffer = ""  # Collect words
    chunks = []  # Store completed sentences

    try:
        with session.post(OLLAMA_URL, json=payload, stream=True, timeout=10) as response:
            if response.status_code == 200:
                print(f"{BOT_NAME}:", end=" ", flush=True)

                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        # Parse JSON response
                        data = json.loads(line.decode("utf-8"))
                        if "response" in data:
                            buffer += data["response"]

                            # Look for sentence-ending punctuation
                            while any(p in buffer for p in [".", "!", "?"]):
                                for p in [".", "!", "?"]:
                                    if p in buffer:
                                        sentence, buffer = buffer.split(p, 1)
                                        sentence = sentence.strip()
                                        if sentence:
                                            chunks.append(sentence)
                                            print(sentence + p, flush=True)

                    except json.JSONDecodeError:
                        continue  # Ignore malformed lines

                # Print any remaining text after streaming ends
                if buffer.strip():
                    chunks.append(buffer.strip())
                    print(buffer.strip(), flush=True)

            else:
                print(f"Error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network error: {e}")

# Main function
if __name__ == '__main__':
    print("Type your message and press Enter. Type 'quit' to exit.")
    
    while True:
        print("\nYou:", end=" ")
        user_input = input().strip()
        if user_input.lower() == 'quit':
            break
        process_text(user_input)

    print("\nGoodbye!")
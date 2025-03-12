import requests
import json
import pyttsx3
from RealtimeSTT import AudioToTextRecorder

# Ollama API URL
OLLAMA_URL = "http://localhost:11434/api/generate"

# Bot's identity
BOT_NAME = "Spera"

# Initialize TTS engine
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 185)  # Adjust speech speed

# Initialize a session for persistent HTTP connection
session = requests.Session()
session.headers.update({"Connection": "keep-alive"})  # Enable Keep-Alive

# Global flag to manage STT recording
recording_active = True

# Function to speak text and pause STT while speaking
def speak_text(text):
    global recording_active

    if not text.strip():
        return

    recording_active = False  # Pause STT
    tts_engine.say(text)
    tts_engine.runAndWait()  # Speak sentence-by-sentence
    recording_active = True  # Resume STT

# Function to process recognized speech
def process_text(text):
    if not text.strip() or not recording_active:
        return

    print(f"\nUser: {text}")  # Display user input

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
                                            speak_text(sentence + p)  # Speak each sentence

                    except json.JSONDecodeError:
                        continue  # Ignore malformed lines

                # Speak any remaining text after streaming ends
                if buffer.strip():
                    chunks.append(buffer.strip())
                    print(buffer.strip(), flush=True)
                    speak_text(buffer.strip())

            else:
                print(f"Error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network error: {e}")

# Main function
if __name__ == '__main__':
    print("Wait until it says 'Speak now'...")
    recorder = AudioToTextRecorder(language="en")

    while True:
        if recording_active:  # Only record if allowed
            text = recorder.text()
            process_text(text)

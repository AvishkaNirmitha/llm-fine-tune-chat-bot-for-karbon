from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from app_9_rag_engine import RAGQueryEngine
import time
import json
import os
from datetime import datetime
import threading


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["25 per minute"]
)

@limiter.request_filter
def exempt_health_check():
    return request.path == "/healthcheck"

@limiter.limit("25 per minute")
def on_limit_exceeded(e):
    return jsonify({
        "error": "Rate limit exceeded. Please wait and try again later.",
    }), 429

ALLOWED_FIELDS = ['message', 'type', 'userid']
engine = RAGQueryEngine()

def save_request_data(request_data, response_data):
    # Create requests-data directory if it doesn't exist
    if not os.path.exists('requests-data'):
        os.makedirs('requests-data')
    
    # Generate filename with current date
    current_date = datetime.now().strftime('%d-%m-%Y')
    filename = f'requests-data/requests-{current_date}.json'
    
    # Prepare data to be saved
    data_to_save = {
        "timestamp": datetime.now().isoformat(),
        "request": request_data,
        "response": response_data
    }
    
    # Load existing data or create new array
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = []
    else:
        existing_data = []
    
    # Append new data and save
    existing_data.append(data_to_save)
    
    with open(filename, 'w') as f:
        json.dump(existing_data, f, indent=2)

@app.route('/api/messages', methods=['POST'])
@limiter.limit("25 per minute", error_message="Too many requests, slow down!")
def create_message():
    request_time = datetime.now().isoformat()
    request_data = request.get_json()

    # Store the original request data
    request_payload = {
        "path": request.path,
        "method": request.method,
        "headers": dict(request.headers),
        "data": request_data,
        "timestamp": request_time
    }

    # Validate the required fields
    if not request_data:
        response_data = {"error": "No input data provided"}
        save_request_data(request_payload, response_data)
        return jsonify(response_data), 400

    missing_fields = [field for field in ALLOWED_FIELDS if field not in request_data]
    if missing_fields:
        response_data = {"error": f"Missing required fields: {', '.join(missing_fields)}"}
        save_request_data(request_payload, response_data)
        return jsonify(response_data), 400

    # Get response from engine
    result = engine.query(request_data['message'])
    
    # Prepare response data
    response_data = {
        "answer": result.answer,
        "token_info": result.token_info,
        "timing": result.timing,
        "context": result.context
    }




  

    # Creating a thread
    thredd = threading.Thread(target=save_request_data,args=(request_payload, response_data))
    thredd.start()

   

    print("Threading done!")


    return jsonify(response_data), 201





@app.route('/api/reactions', methods=['POST'])
@limiter.limit("25 per minute", error_message="Too many requests, slow down!")
def create_reaction():
    try:
        # Create reactions folder if it doesn't exist
        if not os.path.exists('reactions'):
            os.makedirs('reactions')
        
        # Fixed filename for all reactions
        filename = 'reactions/reactions.json'
        
        # Get the payload from request
        payload = request.get_json()
        
        # Add timestamp to payload
        payload['timestamp'] = datetime.now().isoformat()
        
        # Read existing data or create new array
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]
            except json.JSONDecodeError:
                data = []
        else:
            data = []
        
        # Append new payload to array
        data.append(payload)
        
        # Write updated data back to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            "message": "Reaction saved successfully",
            "timestamp": payload['timestamp']
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Failed to save reaction",
            "message": str(e)
        }), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,debug=True)  # Replace 5000 with your desired port if necessary

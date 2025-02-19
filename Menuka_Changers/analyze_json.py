import json
import re

def get_error_msg_and_reason(entry):
    error_response = entry.get("Error(Postman response)")
    reason = entry.get("Reason", "")
    
    if isinstance(error_response, dict):
        return error_response.get("retMsg", ""), reason
    elif isinstance(error_response, str):
        # Try to extract retMsg from JSON string
        match = re.search(r'"retMsg"\s*:\s*"([^"]*)"', error_response)
        if match:
            return match.group(1), reason
    return "", reason

def analyze_json(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    with open(output_file, 'w') as f:
        for i, entry in enumerate(data, start=1):
            error_msg, reason = get_error_msg_and_reason(entry)
            if error_msg and reason:
                f.write(f"{i}. {error_msg} - {reason}\n")

if __name__ == "__main__":
    input_file = "csvjson.json"
    output_file = "output.txt"
    analyze_json(input_file, output_file)

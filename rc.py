from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# Configuration
COVERSURE_API_URL = "https://api.coversure.in/lead/coversure/motor-buying"

# Device details template
DEVICE_DETAILS = {
    "build_id": "BP2A.250605.031.A3",
    "device_name": "AI+ Nova 2 Ultra",
    "manufacturer": "AIPLUS",
    "brand": "AIPLUS",
    "build_number": "115",
    "os_version": "16",
    "hasNotch": False,
    "device_type": "Handset",
    "os_name": "Android",
    "application_version_number": "6.19",
    "application_version_code": "119",
    "deviceId": "7803524bf7e47aac"
}

# Get tokens from environment variables
BEARER_TOKEN = os.environ.get('BEARER_TOKEN', 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJDb3ZlcnN1cmUgVG9rZW4iLCJleHAiOjE3OTQwNzYyMDB9.w8sY27y824Ob6arlimlLGNH-qzHfEBTDf9hMNW0P5WXO0wXv2mv8Ut6wCoI1Gb-q19GvFjQoDicBWCxNLn1IVQ')
USER_TOKEN = os.environ.get('USER_TOKEN', 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjI0MDY0MSwiY2xpZW50SWQiOiIyNTIzMTQ5MDI4NzdDIiwic3ViIjoiOTQ1MjM1Mzk5OSIsImlhdCI6MTc4NjM3OTY4OX0.T_OwQAWwFDaX8Nrk02WOL4wTy2HpKwYRKjXlgASRoIVDQY-STRhmLOAGCLaqu2QxKK3PG68lVjY8iu7BqU92Vg')


@app.route('/', methods=['GET'])
def motor_buying():
    """Main endpoint to proxy Coversure API"""
    
    registration_number = request.args.get('registrationNumber')
    
    if not registration_number:
        return jsonify({
            "success": False,
            "error": "registrationNumber is required"
        }), 400
    
    try:
        params = {
            "registrationNumber": registration_number,
            **DEVICE_DETAILS
        }
        params['hasNotch'] = str(DEVICE_DETAILS['hasNotch']).lower()
        
        headers = {
            'host': 'api.coversure.in',
            'accept': 'application/json, text/plain, */*',
            'authorization': f'Bearer {BEARER_TOKEN}',
            'user-token': USER_TOKEN,
            'devicedetails': json.dumps(DEVICE_DETAILS),
            'device-type': 'android',
            'accept-encoding': 'gzip',
            'user-agent': 'okhttp/4.12.0'
        }
        
        print(f"Fetching data for registration: {registration_number}")
        
        response = requests.get(
            COVERSURE_API_URL,
            params=params,
            headers=headers,
            timeout=30
        )
        
        return jsonify({
            "success": True,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "status_code": response.status_code
        }), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Request timeout",
            "message": "Coversure API took too long to respond"
        }), 504
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Connection error",
            "message": "Failed to connect to Coversure API"
        }), 503
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": "Request failed",
            "message": str(e)
        }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Coversure API Proxy"
    }), 200


# Vercel requires this
app = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

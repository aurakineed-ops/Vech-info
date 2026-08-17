from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Referer": "https://vahanx.in/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

def get_vehicle_details(rc_number: str) -> dict:
    """Scrape vehicle details from vahanx.in"""
    rc = rc_number.strip().upper()
    url = f"https://vahanx.in/rc-search/{rc}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return {"error": f"Failed to fetch: {str(e)}"}

    def get_value(label):
        try:
            div = soup.find("span", string=label)
            if div:
                div = div.find_parent("div")
                p = div.find("p") if div else None
                return p.get_text(strip=True) if p else None
        except:
            return None

    def extract_card(label):
        for div in soup.select(".hrcd-cardbody"):
            span = div.find("span")
            if span and label.lower() in span.text.lower():
                p = div.find("p")
                return p.get_text(strip=True) if p else None
        return None

    def extract_section(header_text, keys):
        section = soup.find("h3", string=lambda s: s and header_text.lower() in s.lower())
        section_card = section.find_parent("div", class_="hrc-details-card") if section else None
        result = {}
        for key in keys:
            span = section_card.find("span", string=lambda s: s and key in s) if section_card else None
            if span:
                val = span.find_next("p")
                result[key.lower().replace(" ", "_")] = val.get_text(strip=True) if val else None
        return result

    try:
        registration = soup.find("h1").text.strip()
    except:
        registration = rc

    ownership = extract_section("Ownership Details", [
        "Owner Name", "Father's Name", "Owner Serial No", "Registered RTO"
    ])

    vehicle = extract_section("Vehicle Details", [
        "Model Name", "Maker Model", "Vehicle Class", "Fuel Type", 
        "Fuel Norms", "Cubic Capacity", "Seating Capacity"
    ])

    insurance = extract_section("Insurance Information", [
        "Insurance Company", "Insurance No", "Insurance Expiry", "Insurance Upto"
    ])

    validity = extract_section("Important Dates", [
        "Registration Date", "Vehicle Age", "Fitness Upto", 
        "Insurance Upto", "Tax Upto", "Tax Paid Upto"
    ])

    puc = extract_section("PUC Details", ["PUC No", "PUC Upto"])
    other = extract_section("Other Information", [
        "Financer Name", "Permit Type", "Blacklist Status", "NOC Details"
    ])

    insurance_expired = soup.select_one(".insurance-alert-box.expired .title")
    insurance_status = "Expired" if insurance_expired else "Active"

    data = {
        "registration_number": registration,
        "status": "success",
        "basic_info": {
            "owner_name": extract_card("Owner Name") or get_value("Owner Name") or ownership.get("owner_name"),
            "model_name": extract_card("Modal Name") or get_value("Model Name") or vehicle.get("model_name"),
            "city": extract_card("City Name") or get_value("City Name"),
            "phone": extract_card("Phone") or get_value("Phone"),
            "address": extract_card("Address") or get_value("Address"),
            "code": extract_card("Code"),
            "website": extract_card("Website")
        },
        "ownership_details": {
            "owner_name": ownership.get("owner_name"),
            "fathers_name": ownership.get("father's_name") or get_value("Father's Name"),
            "serial_no": ownership.get("owner_serial_no"),
            "rto": ownership.get("registered_rto") or get_value("Registered RTO")
        },
        "vehicle_details": {
            "maker": vehicle.get("model_name") or get_value("Model Name"),
            "model": vehicle.get("maker_model") or get_value("Maker Model"),
            "vehicle_class": vehicle.get("vehicle_class") or get_value("Vehicle Class"),
            "fuel_type": vehicle.get("fuel_type") or get_value("Fuel Type"),
            "fuel_norms": vehicle.get("fuel_norms") or get_value("Fuel Norms"),
            "cubic_capacity": vehicle.get("cubic_capacity") or other.get("cubic_capacity") or get_value("Cubic Capacity"),
            "seating_capacity": vehicle.get("seating_capacity") or other.get("seating_capacity") or get_value("Seating Capacity")
        },
        "insurance": {
            "status": insurance_status,
            "company": insurance.get("insurance_company") or get_value("Insurance Company"),
            "policy_number": insurance.get("insurance_no") or get_value("Insurance No"),
            "expiry_date": insurance.get("insurance_expiry") or get_value("Insurance Expiry"),
            "valid_upto": insurance.get("insurance_upto") or get_value("Insurance Upto")
        },
        "validity": {
            "registration_date": validity.get("registration_date") or get_value("Registration Date"),
            "vehicle_age": validity.get("vehicle_age") or get_value("Vehicle Age"),
            "fitness_upto": validity.get("fitness_upto") or get_value("Fitness Upto"),
            "insurance_upto": validity.get("insurance_upto") or get_value("Insurance Upto"),
            "tax_upto": validity.get("tax_upto") or validity.get("tax_paid_upto") or get_value("Tax Upto")
        },
        "puc_details": {
            "puc_number": puc.get("puc_no") or get_value("PUC No"),
            "puc_valid_upto": puc.get("puc_upto") or get_value("PUC Upto")
        },
        "other_info": {
            "financer": other.get("financer_name") or get_value("Financier Name"),
            "permit_type": other.get("permit_type") or get_value("Permit Type"),
            "blacklist_status": other.get("blacklist_status") or get_value("Blacklist Status"),
            "noc": other.get("noc_details") or get_value("NOC Details")
        }
    }

    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() if v is not None and v != ""}
        return d
    
    return clean_dict(data)

# ============= ROUTES =============

@app.route('/', methods=['GET'])
def home():
    """API home page"""
    return jsonify({
        "status": "online",
        "service": "Vehicle Information API",
        "version": "1.0",
        "endpoints": {
            "vehicle_info": "/api/vehicle-info?rc=<RC_NUMBER>",
            "health": "/health"
        },
        "example": "/api/vehicle-info?rc=DL01AB1234",
        "docs": "https://github.com/yourusername/vehicle-api"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Vehicle Information API",
        "timestamp": time.time()
    })

@app.route('/api/vehicle-info', methods=['GET'])
def get_vehicle_info():
    """Get vehicle details by RC number"""
    rc = request.args.get('rc')
    
    if not rc:
        return jsonify({
            "error": "Missing rc parameter",
            "usage": "/api/vehicle-info?rc=<RC_NUMBER>",
            "example": "/api/vehicle-info?rc=DL01AB1234"
        }), 400
    
    try:
        data = get_vehicle_details(rc)
        if data.get("error"):
            return jsonify(data), 404
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Vercel requires this
app = app

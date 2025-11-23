"""CARFAX PDF parser for extracting service records."""
import re
from datetime import datetime
from typing import List, Optional
from pypdf import PdfReader
from pydantic import BaseModel

from app.data.maintenance_schedule import get_service_key, SERVICE_TYPE_MAPPING


class ServiceRecord(BaseModel):
    date: str
    mileage: Optional[int]
    service_type: str
    description: str
    location: Optional[str]
    category: str  # maintenance, repair, inspection, recall


class CarfaxData(BaseModel):
    vin: Optional[str]
    vehicle: Optional[str]
    total_records: int
    service_records: List[ServiceRecord]
    owners: Optional[int]
    accidents: Optional[int]


def extract_mileage(text: str) -> Optional[int]:
    """Extract mileage from text, handling various formats."""
    # Common mileage patterns
    patterns = [
        r"(\d{1,3},?\d{3})\s*(?:miles?|mi\.?)",  # 45,000 miles or 45000 mi
        r"(?:^|\s)(\d{4,6})(?:\s|$)",  # Standalone 5-6 digit number
        r"(\d{1,3},\d{3})",  # Comma-separated number
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mileage_str = match.group(1).replace(",", "")
            try:
                mileage = int(mileage_str)
                # Sanity check - reasonable mileage range
                if 0 < mileage < 500000:
                    return mileage
            except ValueError:
                continue
    return None


def categorize_service(description: str) -> tuple[str, str]:
    """Categorize service and extract service type from description."""
    desc_lower = description.lower()

    # First try to map using our maintenance schedule
    service_key = get_service_key(description)
    if service_key:
        # Get a nice display name
        from app.data.maintenance_schedule import get_maintenance_item
        item = get_maintenance_item(service_key)
        if item:
            return item["name"], "maintenance"

    # Service patterns with categories and display names
    service_patterns = {
        "maintenance": {
            r"oil\s*(?:&|and)?\s*filter": "Oil & Filter Change",
            r"oil\s+change": "Oil Change",
            r"lube\s*[,\s]*oil": "Oil & Filter Change",
            r"tire\s+rotation": "Tire Rotation",
            r"rotate\s+tires?": "Tire Rotation",
            r"balance\s+tires?": "Tire Balance",
            r"wheel\s+alignment": "Wheel Alignment",
            r"air\s+filter": "Air Filter",
            r"engine\s+filter": "Engine Air Filter",
            r"cabin\s+(?:air\s+)?filter": "Cabin Air Filter",
            r"hvac\s+filter": "Cabin Air Filter",
            r"brake\s+fluid": "Brake Fluid Service",
            r"transmission\s+(?:fluid|service)": "Transmission Service",
            r"coolant\s+(?:flush|service)?": "Coolant Service",
            r"antifreeze": "Coolant Service",
            r"spark\s+plug": "Spark Plugs",
            r"battery\s+(?:replace|service|install)": "Battery Service",
            r"wiper\s+blade": "Wiper Blades",
            r"drive\s+belt": "Drive Belt",
            r"serpentine\s+belt": "Serpentine Belt",
            r"timing\s+belt": "Timing Belt",
            r"differential\s+(?:fluid|service)": "Differential Service",
            r"front\s+differential": "Front Differential Service",
            r"rear\s+differential": "Rear Differential Service",
            r"transfer\s+case": "Transfer Case Service",
            r"power\s+steering\s+fluid": "Power Steering Fluid",
            r"multi[- ]?point\s+inspection": "Multi-Point Inspection",
            r"scheduled\s+maintenance": "Scheduled Maintenance",
            r"factory\s+scheduled": "Factory Scheduled Maintenance",
        },
        "repair": {
            r"brake\s+(?:pad|shoe)s?\s+(?:replace|install)": "Brake Pad Replacement",
            r"(?:front|rear)\s+brake\s+(?:pad|shoe)": "Brake Pad Replacement",
            r"rotor\s+(?:replace|resurface|machine)": "Rotor Service",
            r"brake\s+repair": "Brake Repair",
            r"alternator": "Alternator Replacement",
            r"starter\s+(?:motor|replace)": "Starter Replacement",
            r"water\s+pump": "Water Pump Replacement",
            r"thermostat": "Thermostat Replacement",
            r"radiator\s+(?:replace|repair)": "Radiator Service",
            r"a/?c\s+(?:service|repair|recharge)": "A/C Service",
            r"air\s+conditioning": "A/C Service",
            r"suspension\s+(?:repair|service)": "Suspension Repair",
            r"shock\s+(?:absorber)?s?": "Shock Absorber Replacement",
            r"strut": "Strut Replacement",
            r"cv\s+(?:joint|axle|boot)": "CV Joint/Axle Service",
            r"exhaust\s+(?:repair|replace)": "Exhaust Repair",
            r"muffler": "Muffler Replacement",
            r"catalytic\s+converter": "Catalytic Converter",
        },
        "inspection": {
            r"(?:safety|state)\s+inspection": "Safety Inspection",
            r"emissions?\s+(?:test|inspection)": "Emissions Inspection",
            r"smog\s+(?:check|test)": "Smog Check",
            r"vehicle\s+inspection": "Vehicle Inspection",
            r"pre[- ]?purchase\s+inspection": "Pre-Purchase Inspection",
        },
        "recall": {
            r"recall\s+(?:repair|service|performed)": "Recall Service",
            r"safety\s+recall": "Safety Recall",
            r"manufacturer\s+recall": "Manufacturer Recall",
            r"campaign": "Recall Campaign",
        }
    }

    # Search for patterns
    for category, patterns in service_patterns.items():
        for pattern, service_name in patterns.items():
            if re.search(pattern, desc_lower):
                return service_name, category

    # Default categorization based on keywords
    if any(word in desc_lower for word in ["replace", "repair", "fix", "broken"]):
        return "Repair Service", "repair"
    elif any(word in desc_lower for word in ["inspect", "check", "test"]):
        return "Inspection", "inspection"

    return "Service", "maintenance"


def extract_location(text: str) -> Optional[str]:
    """Extract service location from text."""
    # Common location patterns
    patterns = [
        # Named dealerships/shops
        r"(?:at|@|by)\s+([A-Z][A-Za-z\s&']+(?:Toyota|Honda|Ford|Chevrolet|Nissan|Auto|Service|Repair|Tire|Lube)[A-Za-z\s&']*)",
        # City, State pattern
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})",
        # Generic location with common suffixes
        r"(?:at|@|by)\s+([A-Z][A-Za-z\s&']+(?:Inc|LLC|Ltd|Corp|Center|Shop|Garage)\.?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            location = match.group(1).strip()
            # Clean up location
            location = re.sub(r"\s+", " ", location)
            if len(location) > 5:
                return location[:200]  # Truncate to reasonable length

    return None


def extract_service_records(text: str) -> List[ServiceRecord]:
    """Extract service records from CARFAX text."""
    records = []

    # Multiple patterns for different CARFAX formats
    # Format 1: Date followed by mileage on same or next line
    entry_patterns = [
        # Standard format: MM/DD/YYYY followed by mileage and description
        r"(\d{1,2}/\d{1,2}/\d{4})\s*\n?\s*(\d{1,3},?\d{0,3})?\s*(?:miles?)?\s*\n?\s*(.+?)(?=\d{1,2}/\d{1,2}/\d{4}|$)",
        # Alternative with clear mileage marker
        r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:Odometer[:\s]+)?(\d{1,3},?\d{3})\s*(?:miles?)?\s*(.+?)(?=\d{1,2}/\d{1,2}/\d{4}|$)",
    ]

    all_matches = []
    for pattern in entry_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        all_matches.extend(matches)

    # Remove duplicates based on date
    seen_dates = set()
    unique_matches = []
    for match in all_matches:
        date_str = match[0]
        if date_str not in seen_dates:
            seen_dates.add(date_str)
            unique_matches.append(match)

    for match in unique_matches:
        date_str, mileage_str, description = match

        # Clean up mileage
        mileage = None
        if mileage_str:
            mileage = int(mileage_str.replace(",", ""))

        # If no mileage found in pattern, try to extract from description
        if not mileage:
            mileage = extract_mileage(description)

        # Clean up description
        description = " ".join(description.split())
        description = re.sub(r"^\s*[-•]\s*", "", description)  # Remove bullet points

        if not description or len(description) < 3:
            continue

        # Categorize and get service type
        service_type, category = categorize_service(description)

        # Extract location
        location = extract_location(description)

        # Clean description - remove redundant service type mentions
        clean_desc = description
        if len(clean_desc) > 500:
            clean_desc = clean_desc[:497] + "..."

        records.append(ServiceRecord(
            date=date_str,
            mileage=mileage,
            service_type=service_type[:200],
            description=clean_desc,
            location=location,
            category=category
        ))

    # Sort by date (newest first) then by mileage
    records.sort(key=lambda r: (
        datetime.strptime(r.date, "%m/%d/%Y") if "/" in r.date else datetime.min,
        r.mileage or 0
    ), reverse=True)

    return records


def parse_carfax_pdf(file_path: str) -> CarfaxData:
    """Parse a CARFAX PDF and extract vehicle and service data."""
    reader = PdfReader(file_path)

    full_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n"

    # Extract VIN (17 characters, excluding I, O, Q)
    vin_match = re.search(r"VIN[:\s]*([A-HJ-NPR-Z0-9]{17})", full_text, re.IGNORECASE)
    vin = vin_match.group(1) if vin_match else None

    # Extract vehicle info - try multiple patterns
    vehicle = None
    vehicle_patterns = [
        r"(\d{4})\s+(Toyota\s+[\w\s]+?)(?:\n|VIN|CARFAX)",
        r"(\d{4})\s+([\w]+\s+[\w]+)(?:\s+VIN|\s+\n)",
        r"Vehicle:\s*(\d{4})\s+(.+?)(?:\n|$)",
    ]
    for pattern in vehicle_patterns:
        vehicle_match = re.search(pattern, full_text, re.IGNORECASE)
        if vehicle_match:
            year = vehicle_match.group(1)
            model = vehicle_match.group(2).strip()
            vehicle = f"{year} {model}"
            break

    # Extract owner count
    owner_match = re.search(r"(\d+)\s*-?\s*(?:owner|Owner)", full_text)
    owners = int(owner_match.group(1)) if owner_match else None

    # Check for accidents
    accidents = 0
    accident_patterns = [
        r"(\d+)\s+(?:accident|Accident|damage\s+report)",
        r"Accidents?\s*(?:Reported)?[:\s]+(\d+)",
    ]
    for pattern in accident_patterns:
        accident_match = re.search(pattern, full_text, re.IGNORECASE)
        if accident_match:
            accidents = int(accident_match.group(1))
            break

    # Check for "no accidents" phrases
    if re.search(r"No\s+(?:accidents?|damage)\s+(?:reported|found)", full_text, re.IGNORECASE):
        accidents = 0

    # Extract service records
    service_records = extract_service_records(full_text)

    return CarfaxData(
        vin=vin,
        vehicle=vehicle,
        total_records=len(service_records),
        service_records=service_records,
        owners=owners,
        accidents=accidents
    )


def convert_to_maintenance_records(carfax_data: CarfaxData) -> List[dict]:
    """Convert CARFAX service records to maintenance log format."""
    maintenance_records = []

    for record in carfax_data.service_records:
        # Parse date
        try:
            date_obj = datetime.strptime(record.date, "%m/%d/%Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = record.date

        maintenance_records.append({
            "date": formatted_date,
            "mileage": record.mileage,
            "service_type": record.service_type,
            "description": record.description,
            "category": record.category,
            "source": "CARFAX",
            "location": record.location
        })

    return maintenance_records

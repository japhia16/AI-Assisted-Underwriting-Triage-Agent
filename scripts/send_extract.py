import requests
import json

payload = '''COMMERCIAL PROPERTY STATEMENT OF VALUES
Account: 99-882-110
Client: Emerald City Highrise Corp.
Address: 400 Broad St, Seattle, WA 98109
Construction Class: Fire Resistive (ISO Class 6)
Total Sum Insured: $40,000,000
Property Deductible: $100,000
Occupancy: Warehouse
Industry: Textiles & Garments
Age: 25 years
Employees: 120
Prior Claims: 2
Sprinkler System: No
Fire Hydrant Onsite: Yes
Requested Coverage: Standard Fire & Special Perils
'''

resp = requests.post('http://127.0.0.1:8000/extract', json={'text': payload})
print('STATUS', resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)

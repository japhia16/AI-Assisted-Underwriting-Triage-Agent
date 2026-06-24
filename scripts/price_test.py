import requests, json
s='''COMMERCIAL PROPERTY STATEMENT OF VALUES
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

r = requests.post('http://127.0.0.1:8000/extract', json={'text': s}, timeout=10)
print('extract status', r.status_code)
print(json.dumps(r.json(), indent=2))
if r.status_code==200 and r.json().get('status')=='complete':
    p = requests.post('http://127.0.0.1:8000/price', json={'submission_json': r.json()['submission_json']}, timeout=60)
    print('price status', p.status_code)
    print(json.dumps(p.json(), indent=2))
else:
    print('Extraction incomplete; not calling price')

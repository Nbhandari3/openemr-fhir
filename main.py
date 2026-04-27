"""
OpenEMR FHIR-compliant EHR Backend - No pydantic dependency
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime
from typing import Optional

app = FastAPI(title="OpenEMR FHIR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory FHIR store ─────────────────────────────────────────────────────

patients = {}   # mrn -> dict
conditions = {} # mrn -> dict

def make_patient(mrn, name, gender, age, address):
    parts = name.strip().split(" ", 1)
    return {
        "resourceType": "Patient",
        "id": mrn,
        "name": [{"use": "official", "text": name,
                  "given": [parts[0]], "family": parts[1] if len(parts) > 1 else ""}],
        "gender": gender.lower(),
        "age": age,
        "address": [{"use": "home", "text": address, "country": "US"}],
        "active": True,
        "meta": {"lastUpdated": datetime.utcnow().isoformat() + "Z",
                 "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]}
    }

def make_condition(mrn, diagnosis, treatment):
    return {
        "resourceType": "Condition",
        "subject_ref": mrn,
        "code": {"text": diagnosis},
        "treatment": treatment
    }

def summary(mrn):
    p = patients[mrn]
    c = conditions.get(mrn, {})
    return {
        "mrn": mrn,
        "name": p["name"][0]["text"],
        "gender": p["gender"],
        "age": p["age"],
        "address": p["address"][0]["text"] if p["address"] else "",
        "diagnosis": c.get("code", {}).get("text", ""),
        "treatment": c.get("treatment", ""),
        "lastUpdated": p["meta"]["lastUpdated"],
    }

# ─── Seed Data ────────────────────────────────────────────────────────────────

_seed = [
    ("1145980","Michael Smith","Male",28,"100 Main St Atlanta GA","Flu","Antiviral Medication"),
    ("1145981","Mary Brown","Female",32,"251 Spring Street Kennesaw GA","Cold","Rest and Hydration"),
    ("1145982","John Miller","Male",18,"5th Street Morrow GA","Arthritis","Painkillers"),
    ("1145983","Brian Martinez","Male",25,"25 Washington Way Marrietta GA","Diabetes","Medication & Insulin"),
    ("1145984","Aubrey Gonzales","Female",20,"101 President Road Johns Creek GA","Asthma","Inhaler & Medication"),
    ("1145985","Jeffrey Thomas","Male",30,"350 Swiss Road Cumming GA","Anxiety","Therapy"),
    ("1145986","Erica Jackson","Female",23,"200 Kuhl Ave Atlanta GA","Heart Disease","Angioplasty"),
    ("1145987","Bella Blackman","Female",13,"70 Lake St Macon GA","Cold","Rest and Hydration"),
    ("1145988","Rheinhart Chandler","Male",44,"31 Redsea Way Lawrenceville GA","Flu","Antiviral Medication"),
    ("1145989","John Knoedler","Male",56,"55 River Drive Alpharetta GA","Diabetes","Medication & Insulin"),
    ("1145990","Adira Miller","Female",61,"16 Safe Lane Riverdale GA","Asthma","Inhaler & Medication"),
    ("1145991","Jason Davis","Male",90,"560 Creek Side Way Snellville GA","Cancer","Chemotherapy"),
]

for mrn, name, gender, age, address, diagnosis, treatment in _seed:
    patients[mrn] = make_patient(mrn, name, gender, age, address)
    conditions[mrn] = make_condition(mrn, diagnosis, treatment)

# ─── FHIR Endpoints ───────────────────────────────────────────────────────────

@app.get("/fhir/Patient")
def list_patients():
    entries = [summary(mrn) for mrn in patients]
    return {"resourceType": "Bundle", "type": "searchset",
            "total": len(entries), "entry": [{"resource": e} for e in entries]}

@app.get("/fhir/Patient/{mrn}")
def get_patient(mrn: str):
    if mrn not in patients:
        raise HTTPException(404, detail=f"Patient {mrn} not found")
    return summary(mrn)

@app.post("/fhir/Patient", status_code=201)
async def create_patient(req: dict):
    mrn = req.get("mrn", "").strip()
    name = req.get("name", "").strip()
    if not mrn or not name:
        raise HTTPException(400, detail="mrn and name are required")
    if mrn in patients:
        raise HTTPException(409, detail="Patient MRN already exists")
    patients[mrn] = make_patient(mrn, name, req.get("gender","Other"),
                                  int(req.get("age", 0)), req.get("address",""))
    conditions[mrn] = make_condition(mrn, req.get("diagnosis",""), req.get("treatment",""))
    return {"message": f"Patient {name} registered", "mrn": mrn}

@app.put("/fhir/Patient/{mrn}")
async def update_patient(mrn: str, req: dict):
    if mrn not in patients:
        raise HTTPException(404, detail="Patient not found")
    p = patients[mrn]
    c = conditions.get(mrn, {})
    if "name" in req:
        parts = req["name"].strip().split(" ", 1)
        p["name"] = [{"use":"official","text":req["name"],
                      "given":[parts[0]],"family":parts[1] if len(parts)>1 else ""}]
    if "gender" in req:
        p["gender"] = req["gender"].lower()
    if "age" in req:
        p["age"] = int(req["age"])
    if "address" in req:
        p["address"] = [{"use":"home","text":req["address"],"country":"US"}]
    if "diagnosis" in req and c:
        c["code"]["text"] = req["diagnosis"]
    if "treatment" in req and c:
        c["treatment"] = req["treatment"]
    p["meta"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
    return {"message": "Patient updated", "mrn": mrn}

@app.delete("/fhir/Patient/{mrn}")
def delete_patient(mrn: str):
    if mrn not in patients:
        raise HTTPException(404, detail="Patient not found")
    name = patients[mrn]["name"][0]["text"]
    del patients[mrn]
    conditions.pop(mrn, None)
    return {"message": f"Patient {name} deleted", "mrn": mrn}

@app.get("/fhir/stats")
def get_stats():
    total = len(patients)
    male = sum(1 for p in patients.values() if p["gender"] == "male")
    female = sum(1 for p in patients.values() if p["gender"] == "female")
    recent = [summary(mrn) for mrn in list(patients.keys())[-6:]][::-1]
    return {"total": total, "male": male, "female": female, "recent": recent}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse("static/index.html")

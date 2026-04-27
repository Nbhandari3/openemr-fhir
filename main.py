"""
OpenEMR FHIR-compliant EHR Backend
FHIR R4 Patient resource: https://www.hl7.org/fhir/patient.html
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

app = FastAPI(title="OpenEMR FHIR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── FHIR R4 Models ──────────────────────────────────────────────────────────

class HumanName(BaseModel):
    use: str = "official"
    text: str
    family: Optional[str] = None
    given: Optional[List[str]] = None

class Address(BaseModel):
    use: str = "home"
    text: str
    country: str = "US"

class CodeableConcept(BaseModel):
    text: str

class Condition(BaseModel):
    resourceType: str = "Condition"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject_ref: str
    code: CodeableConcept
    treatment: str

class Patient(BaseModel):
    resourceType: str = "Patient"
    id: str
    name: List[HumanName]
    gender: str
    age: Optional[int] = None
    address: Optional[List[Address]] = None
    active: bool = True
    meta: dict = Field(default_factory=lambda: {
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
    })

class PatientCreate(BaseModel):
    mrn: str
    name: str
    gender: str
    age: int
    address: str
    diagnosis: str
    treatment: str

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    address: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def build_patient(mrn, name, gender, age, address):
    parts = name.strip().split(" ", 1)
    return Patient(
        id=mrn,
        name=[HumanName(text=name, given=[parts[0]], family=parts[1] if len(parts) > 1 else "")],
        gender=gender.lower(),
        age=age,
        address=[Address(text=address)]
    )

def make_condition(mrn, diagnosis, treatment):
    return Condition(subject_ref=mrn, code=CodeableConcept(text=diagnosis), treatment=treatment)

def patient_summary(mrn):
    p = patients[mrn]
    c = conditions.get(mrn)
    return {
        "mrn": mrn,
        "name": p.name[0].text,
        "gender": p.gender,
        "age": p.age,
        "address": p.address[0].text if p.address else "",
        "diagnosis": c.code.text if c else "",
        "treatment": c.treatment if c else "",
        "lastUpdated": p.meta.get("lastUpdated", ""),
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

patients = {}
conditions = {}

for mrn, name, gender, age, address, diagnosis, treatment in _seed:
    patients[mrn] = build_patient(mrn, name, gender, age, address)
    conditions[mrn] = make_condition(mrn, diagnosis, treatment)


# ─── FHIR Endpoints ───────────────────────────────────────────────────────────

@app.get("/fhir/Patient")
def list_patients():
    summaries = [patient_summary(mrn) for mrn in patients]
    return {"resourceType": "Bundle", "type": "searchset", "total": len(summaries),
            "entry": [{"resource": s} for s in summaries]}

@app.get("/fhir/Patient/{mrn}")
def get_patient(mrn: str):
    if mrn not in patients:
        raise HTTPException(404, detail=f"Patient {mrn} not found")
    return patient_summary(mrn)

@app.post("/fhir/Patient", status_code=201)
def create_patient(body: PatientCreate):
    if body.mrn in patients:
        raise HTTPException(409, detail="Patient MRN already exists")
    patients[body.mrn] = build_patient(body.mrn, body.name, body.gender, body.age, body.address)
    conditions[body.mrn] = make_condition(body.mrn, body.diagnosis, body.treatment)
    return {"message": f"Patient {body.name} registered", "mrn": body.mrn}

@app.put("/fhir/Patient/{mrn}")
def update_patient(mrn: str, body: PatientUpdate):
    if mrn not in patients:
        raise HTTPException(404, detail="Patient not found")
    p = patients[mrn]
    c = conditions.get(mrn)
    if body.name:
        parts = body.name.strip().split(" ", 1)
        p.name = [HumanName(text=body.name, given=[parts[0]], family=parts[1] if len(parts) > 1 else "")]
    if body.gender:
        p.gender = body.gender.lower()
    if body.age is not None:
        p.age = body.age
    if body.address:
        p.address = [Address(text=body.address)]
    if body.diagnosis and c:
        c.code.text = body.diagnosis
    if body.treatment and c:
        c.treatment = body.treatment
    p.meta["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
    return {"message": "Patient updated", "mrn": mrn}

@app.delete("/fhir/Patient/{mrn}")
def delete_patient(mrn: str):
    if mrn not in patients:
        raise HTTPException(404, detail="Patient not found")
    name = patients[mrn].name[0].text
    del patients[mrn]
    conditions.pop(mrn, None)
    return {"message": f"Patient {name} deleted", "mrn": mrn}

@app.get("/fhir/stats")
def get_stats():
    total = len(patients)
    male = sum(1 for p in patients.values() if p.gender == "male")
    female = sum(1 for p in patients.values() if p.gender == "female")
    recent = [patient_summary(mrn) for mrn in list(patients.keys())[-6:]][::-1]
    return {"total": total, "male": male, "female": female, "recent": recent}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse("static/index.html")

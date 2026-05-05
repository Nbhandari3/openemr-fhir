# OpenEMR FHIR-Compliant EHR API

**[▶ Live Demo](https://openemr-fhir-1.onrender.com/)**  
**[▶ Interactive API Docs](https://openemr-fhir-1.onrender.com/)**

> ⚠️ Hosted on Render free tier — first load may take 30–60 seconds to wake up.

A production-style FHIR-compliant Electronic Health Records REST API built 
with FastAPI. Supports full CRUD operations on patient records following the 
HL7 FHIR standard used in real hospital systems.

---

## Features
- 🏥 FHIR HL7-compliant patient resource structure
- 📋 Full CRUD — create, read, update, and delete patient records
- 📊 Dashboard statistics endpoint (total, male/female breakdown, recent admissions)
- 🌐 CORS-enabled for frontend integration
- ⚡ Auto-generated interactive Swagger UI at `/docs`
- 🗂️ Pre-seeded with 12 realistic patient records across Georgia

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fhir/Patient` | List all patients |
| GET | `/fhir/Patient/{mrn}` | Get patient by MRN |
| POST | `/fhir/Patient` | Register new patient |
| PUT | `/fhir/Patient/{mrn}` | Update patient record |
| DELETE | `/fhir/Patient/{mrn}` | Delete patient record |
| GET | `/fhir/stats` | Dashboard statistics |

---

## Tech Stack
- **Python** — core language
- **FastAPI** — REST API framework
- **Uvicorn** — ASGI server
- **FHIR HL7** — healthcare interoperability standard
- **Render** — cloud deployment

---

## Run Locally

```bash

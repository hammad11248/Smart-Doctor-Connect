# 🏥 Smart-Doctor-Connect-AI — OneRecord: Universal Health ID

**MTM (Mind-to-Machine) AI Hackathon — GDGoC CUI Wah**

> An AI-powered healthcare platform that instantly connects patients with the right doctors across Pakistan — using intelligent symptom analysis, real-time appointment booking, and an automated AI receptionist.

---

## 🚀 What It Does

Accessing healthcare in Pakistan is fragmented and slow. Smart-Doctor-Connect-AI solves this with a single intelligent platform:

| Feature | Description |
|---|---|
| 🔍 **AI Doctor Search** | Patient describes symptoms → AI maps to the right specialization → returns ranked doctors |
| 📅 **Smart Booking** | Real-time slot availability, conflict-free scheduling, predicted wait times |
| 🤖 **AI Receptionist** | When a doctor is offline, AI collects patient data & sends email notification |
| 👨‍⚕️ **Doctor Profiles** | Doctors register with specialization, location, availability & consultation type |
| 📧 **Auto Follow-ups** | Scheduled reminders sent to patients via email automatically |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python FastAPI (async) |
| **Database** | MongoDB Atlas (Motor async driver) |
| **AI / NLP** | LangChain + OpenRouter (Mistral-7B) |
| **Frontend** | HTML5 + Vanilla JS + Tailwind CSS |
| **Deployment** | Vercel (Serverless) |

---

## 🧠 AI Architecture

### Dual-Engine Recommendation System

```
Patient Input → LangChain LLM (Mistral-7B via OpenRouter)
                        ↓ (fallback)
              Rule-Based Engine (100+ symptom→specialization pairs)
                        ↓
              MongoDB Query + Scoring Algorithm
                        ↓
              Ranked Doctor List (match score 0–100)
```

- **LLM Path**: Context-aware analysis with medical triage prompts
- **Rule-Based Fallback**: 100+ symptom mappings across 15+ medical domains — works offline, always
- **Scoring**: Specialization (50pts) + Location (30pts) + Availability (10pts) + Rating (10pts)

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.11+
- MongoDB Atlas account ([free tier](https://www.mongodb.com/atlas))
- OpenRouter API key ([free at openrouter.ai](https://openrouter.ai))

### 1. Clone & Install

```bash
git clone https://github.com/your-username/smart-doctor-connect-ai.git
cd smart-doctor-connect-ai
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/smart_doctor_db
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
SECRET_KEY=your-random-secret-key
ENVIRONMENT=development
```

| Variable | Description |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string. Get it from your Atlas dashboard → Connect → Drivers. |
| `OPENROUTER_API_KEY` | Free API key from [openrouter.ai](https://openrouter.ai). Used for Mistral-7B LLM calls. |
| `SECRET_KEY` | Any random string for internal signing. |
| `ENVIRONMENT` | Set to `development` for local (enables docs at `/api/docs`). |

### 3. Seed Demo Data

```bash
python seed_data.py
```

### 4. Run Locally

```bash
uvicorn api.main:app --reload --port 8000
```

Visit **http://localhost:8000**

### 5. Deploy to Vercel

```bash
npm i -g vercel
vercel --prod
```

Set your environment variables in the Vercel dashboard under **Settings → Environment Variables**.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/doctors/` | Register a doctor |
| `GET` | `/api/doctors/search?q=back+pain` | AI-powered doctor search |
| `GET` | `/api/doctors/{id}` | Get doctor profile |
| `PUT` | `/api/doctors/{id}` | Update doctor profile |
| `POST` | `/api/appointments/` | Book an appointment |
| `GET` | `/api/appointments/available-slots/{id}?date=YYYY-MM-DD` | Get free time slots |
| `PATCH` | `/api/appointments/{id}/status` | Update appointment status |
| `POST` | `/api/chat/message` | Send message → AI responds |
| `GET` | `/api/chat/history/{doctor_id}` | Get chat history |

---

## 🌟 What Makes This Stand Out

1. **Dual AI Engine** — LLM + rule-based fallback means the recommendation system never fails
2. **Zero Double-Booking** — enforced at the database level with a MongoDB unique compound index
3. **Pakistan-Specific** — symptom maps, city detection, and AI prompts tuned for Pakistani healthcare
4. **Production-Ready** — async throughout, indexed queries, proper error handling, rate limiting
5. **Fully Deployable** — one `vercel --prod` command and it's live

---

## 📄 License

Built for the MTM AI Hackathon by GDGoC CUI Wah.

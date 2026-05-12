"""
Smart Doctor Connect AI — Symptom Recommender Service
Two-stage pipeline:
  1. LangChain LLM (Mistral-7B via OpenRouter) — rich, context-aware analysis
  2. Rule-based fallback (100+ symptom→specialization pairs) — always works
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# ── 100+ Rule-Based Symptom Map ───────────────────────────────────────────────
SYMPTOM_MAP: Dict[str, List[str]] = {
    # Cardiology
    "chest pain": ["Cardiologist", "General Physician"],
    "chest tightness": ["Cardiologist"],
    "heart palpitations": ["Cardiologist"],
    "shortness of breath": ["Cardiologist", "Pulmonologist"],
    "high blood pressure": ["Cardiologist"],
    "irregular heartbeat": ["Cardiologist"],

    # Dermatology
    "skin rash": ["Dermatologist"],
    "acne": ["Dermatologist"],
    "eczema": ["Dermatologist"],
    "psoriasis": ["Dermatologist"],
    "hair loss": ["Dermatologist"],
    "itchy skin": ["Dermatologist"],
    "skin allergy": ["Dermatologist", "Allergist"],
    "fungal infection": ["Dermatologist"],

    # Pediatrics
    "child fever": ["Pediatrician"],
    "baby cough": ["Pediatrician"],
    "child vomiting": ["Pediatrician"],
    "infant rash": ["Pediatrician"],
    "child diarrhea": ["Pediatrician"],
    "vaccination": ["Pediatrician"],
    "growth concern": ["Pediatrician"],
    "my child": ["Pediatrician"],
    "my baby": ["Pediatrician"],

    # Orthopedics
    "back pain": ["Orthopedic Surgeon", "General Physician"],
    "joint pain": ["Orthopedic Surgeon", "Rheumatologist"],
    "knee pain": ["Orthopedic Surgeon"],
    "bone fracture": ["Orthopedic Surgeon"],
    "shoulder pain": ["Orthopedic Surgeon"],
    "neck pain": ["Orthopedic Surgeon", "Neurologist"],
    "arthritis": ["Rheumatologist", "Orthopedic Surgeon"],
    "muscle pain": ["Orthopedic Surgeon", "General Physician"],

    # Gastroenterology
    "stomach pain": ["Gastroenterologist", "General Physician"],
    "abdominal pain": ["Gastroenterologist"],
    "acid reflux": ["Gastroenterologist"],
    "nausea": ["Gastroenterologist", "General Physician"],
    "vomiting": ["Gastroenterologist", "General Physician"],
    "diarrhea": ["Gastroenterologist", "General Physician"],
    "constipation": ["Gastroenterologist"],
    "bloating": ["Gastroenterologist"],
    "jaundice": ["Gastroenterologist", "Hepatologist"],
    "liver": ["Hepatologist", "Gastroenterologist"],

    # Neurology
    "headache": ["Neurologist", "General Physician"],
    "migraine": ["Neurologist"],
    "seizure": ["Neurologist"],
    "dizziness": ["Neurologist", "ENT Specialist"],
    "memory loss": ["Neurologist"],
    "numbness": ["Neurologist"],
    "tingling": ["Neurologist"],
    "stroke": ["Neurologist"],

    # ENT
    "ear pain": ["ENT Specialist"],
    "hearing loss": ["ENT Specialist"],
    "sore throat": ["ENT Specialist", "General Physician"],
    "tonsils": ["ENT Specialist"],
    "sinusitis": ["ENT Specialist"],
    "runny nose": ["ENT Specialist", "General Physician"],
    "nasal congestion": ["ENT Specialist"],
    "tinnitus": ["ENT Specialist"],

    # Pulmonology
    "cough": ["Pulmonologist", "General Physician"],
    "asthma": ["Pulmonologist"],
    "wheezing": ["Pulmonologist"],
    "tuberculosis": ["Pulmonologist"],
    "breathing difficulty": ["Pulmonologist", "Cardiologist"],
    "lung infection": ["Pulmonologist"],

    # Endocrinology & Diabetes
    "diabetes": ["Endocrinologist"],
    "thyroid": ["Endocrinologist"],
    "weight gain": ["Endocrinologist", "General Physician"],
    "weight loss": ["Endocrinologist", "General Physician"],
    "fatigue": ["Endocrinologist", "General Physician"],
    "excessive thirst": ["Endocrinologist"],
    "frequent urination": ["Endocrinologist", "Urologist"],

    # Urology & Nephrology
    "kidney pain": ["Nephrologist", "Urologist"],
    "kidney stone": ["Urologist"],
    "urinary infection": ["Urologist"],
    "blood in urine": ["Urologist", "Nephrologist"],
    "prostate": ["Urologist"],

    # Gynecology & Obstetrics
    "pregnancy": ["Gynecologist", "Obstetrician"],
    "menstrual": ["Gynecologist"],
    "pcos": ["Gynecologist", "Endocrinologist"],
    "fertility": ["Gynecologist"],
    "vaginal discharge": ["Gynecologist"],
    "menopause": ["Gynecologist"],

    # Ophthalmology
    "eye pain": ["Ophthalmologist"],
    "blurry vision": ["Ophthalmologist"],
    "red eye": ["Ophthalmologist"],
    "cataract": ["Ophthalmologist"],
    "glasses": ["Ophthalmologist"],

    # Psychiatry & Mental Health
    "depression": ["Psychiatrist", "Psychologist"],
    "anxiety": ["Psychiatrist", "Psychologist"],
    "stress": ["Psychiatrist", "Psychologist"],
    "insomnia": ["Psychiatrist", "Neurologist"],
    "panic attack": ["Psychiatrist"],
    "mental health": ["Psychiatrist", "Psychologist"],
    "addiction": ["Psychiatrist"],

    # Dentistry
    "tooth pain": ["Dentist"],
    "toothache": ["Dentist"],
    "gum bleeding": ["Dentist"],
    "cavity": ["Dentist"],
    "wisdom tooth": ["Dentist"],

    # General / Infectious
    "fever": ["General Physician"],
    "flu": ["General Physician"],
    "cold": ["General Physician"],
    "infection": ["General Physician"],
    "allergy": ["Allergist", "General Physician"],
    "covid": ["General Physician", "Pulmonologist"],
}

URGENCY_MAP: Dict[str, str] = {
    "chest pain": "HIGH",
    "stroke": "EMERGENCY",
    "seizure": "EMERGENCY",
    "heart palpitations": "HIGH",
    "shortness of breath": "HIGH",
    "blood in urine": "HIGH",
    "jaundice": "HIGH",
    "fever": "MEDIUM",
    "headache": "LOW",
    "back pain": "LOW",
    "acne": "LOW",
}


class SymptomRecommender:
    """
    Analyses a patient's free-text symptom description and returns
    specializations, urgency, and home advice.

    Falls back to rule-based matching if the LLM call fails.
    """

    def __init__(self):
        self._llm = None  # lazy-loaded
        self._llm_available = True

    def _get_llm(self):
        if not self._llm_available:
            return None
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                self._llm_available = False
                return None

            self._llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                model="mistralai/mistral-7b-instruct",
                temperature=0.2,
                max_tokens=512,
            )
            return self._llm
        except Exception:
            self._llm_available = False
            return None

    # ── Rule-Based Fallback ───────────────────────────────────────────────────
    def _rule_based(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        matched_specs: List[str] = []
        urgency = "LOW"

        for keyword, specs in SYMPTOM_MAP.items():
            if keyword in lower:
                for s in specs:
                    if s not in matched_specs:
                        matched_specs.append(s)
                if keyword in URGENCY_MAP:
                    candidate = URGENCY_MAP[keyword]
                    if {"EMERGENCY": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(
                        candidate, 0
                    ) > {"EMERGENCY": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(urgency, 0):
                        urgency = candidate

        if not matched_specs:
            matched_specs = ["General Physician"]

        home_advice = {
            "EMERGENCY": "Please call emergency services (115) immediately or go to the nearest A&E.",
            "HIGH": "Seek medical attention today. Do not delay.",
            "MEDIUM": "Rest, stay hydrated, and book an appointment soon.",
            "LOW": "Monitor symptoms. Stay hydrated and rest. Book an appointment if symptoms persist.",
        }[urgency]

        return {
            "specializations": matched_specs[:3],
            "urgency": urgency,
            "home_advice": home_advice,
        }

    # ── LLM Analysis ─────────────────────────────────────────────────────────
    async def _llm_analyse(self, text: str) -> Dict[str, Any] | None:
        llm = self._get_llm()
        if llm is None:
            return None

        prompt = f"""You are a Pakistani medical triage assistant.
Analyse the patient's description and respond ONLY with valid JSON — no extra text.

Patient says: "{text}"

Respond exactly like this:
{{
  "specializations": ["Specialization1", "Specialization2"],
  "urgency": "LOW|MEDIUM|HIGH|EMERGENCY",
  "home_advice": "One helpful sentence in plain English."
}}
"""
        try:
            from langchain_core.messages import HumanMessage  # noqa: PLC0415

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            # Validate required keys
            assert "specializations" in data and "urgency" in data
            return data
        except Exception:
            self._llm_available = False
            return None

    # ── Public API ────────────────────────────────────────────────────────────
    async def analyse(self, text: str) -> Dict[str, Any]:
        """Return analysis dict. Always succeeds (falls back to rules)."""
        result = await self._llm_analyse(text)
        if result is None:
            result = self._rule_based(text)
        return result

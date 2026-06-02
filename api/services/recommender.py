"""
Smart-Doctor-Connect-AI — Symptom Recommender Service
Two-stage pipeline:
  1. LangChain LLM (Mistral-7B via OpenRouter) — rich, context-aware analysis
  2. Rule-based fallback (100+ symptom→specialization pairs) — always works
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# ── Specialization Synonym Map ────────────────────────────────────────────────
# Maps common search terms / LLM output variants to the exact DB specialization values.
SPECIALIZATION_SYNONYMS: Dict[str, str] = {
    "cardiology": "Cardiologist",
    "heart doctor": "Cardiologist",
    "heart specialist": "Cardiologist",
    "dermatology": "Dermatologist",
    "skin doctor": "Dermatologist",
    "skin specialist": "Dermatologist",
    "pediatrics": "Pediatrician",
    "child doctor": "Pediatrician",
    "child specialist": "Pediatrician",
    "orthopedics": "Orthopedic Surgeon",
    "orthopedic": "Orthopedic Surgeon",
    "bone doctor": "Orthopedic Surgeon",
    "bone specialist": "Orthopedic Surgeon",
    "gastroenterology": "Gastroenterologist",
    "stomach doctor": "Gastroenterologist",
    "neurology": "Neurologist",
    "brain doctor": "Neurologist",
    "brain specialist": "Neurologist",
    "ent": "ENT Specialist",
    "ear nose throat": "ENT Specialist",
    "pulmonology": "Pulmonologist",
    "lung doctor": "Pulmonologist",
    "lung specialist": "Pulmonologist",
    "chest specialist": "Pulmonologist",
    "endocrinology": "Endocrinologist",
    "diabetes doctor": "Endocrinologist",
    "thyroid doctor": "Endocrinologist",
    "urology": "Urologist",
    "kidney doctor": "Nephrologist",
    "nephrology": "Nephrologist",
    "gynecology": "Gynecologist",
    "women doctor": "Gynecologist",
    "women specialist": "Gynecologist",
    "obstetrics": "Gynecologist",
    "ophthalmology": "Ophthalmologist",
    "eye doctor": "Ophthalmologist",
    "eye specialist": "Ophthalmologist",
    "psychiatry": "Psychiatrist",
    "mental health doctor": "Psychiatrist",
    "psychology": "Psychologist",
    "dentistry": "Dentist",
    "dental": "Dentist",
    "allergy": "Allergist",
    "allergy doctor": "Allergist",
    "rheumatology": "Rheumatologist",
    "general medicine": "General Physician",
    "general doctor": "General Physician",
    "family doctor": "General Physician",
    "gp": "General Physician",
}


def normalize_specializations(specs: list) -> list:
    """Normalize specialization names using the synonym map."""
    normalized = []
    for spec in specs:
        lower = spec.lower().strip()
        # Check if it's a synonym
        if lower in SPECIALIZATION_SYNONYMS:
            canonical = SPECIALIZATION_SYNONYMS[lower]
            if canonical not in normalized:
                normalized.append(canonical)
        else:
            # Keep as-is but also try to match partial synonyms
            matched = False
            for synonym, canonical in SPECIALIZATION_SYNONYMS.items():
                if synonym in lower or lower in synonym:
                    if canonical not in normalized:
                        normalized.append(canonical)
                    matched = True
                    break
            if not matched and spec not in normalized:
                normalized.append(spec)
    return normalized


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

    def _get_llm(self):
        """Return cached LLM instance, or create one. Returns None if API key missing."""
        if self._llm is not None:
            return self._llm
        try:
            from langchain_openai import ChatOpenAI  # noqa: PLC0415

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
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

        # Broad fuzzy fallback if no exact keyphrase matched
        if not matched_specs:
            broad_map = {
                "heart": ["Cardiologist"],
                "chest": ["Cardiologist"],
                "cardio": ["Cardiologist"],
                "blood pressure": ["Cardiologist"],
                "bp": ["Cardiologist"],
                
                "skin": ["Dermatologist"],
                "rash": ["Dermatologist"],
                "acne": ["Dermatologist"],
                "pimple": ["Dermatologist"],
                "itch": ["Dermatologist"],
                "hair": ["Dermatologist"],
                
                "child": ["Pediatrician"],
                "baby": ["Pediatrician"],
                "infant": ["Pediatrician"],
                "kid": ["Pediatrician"],
                "pediatric": ["Pediatrician"],
                
                "head": ["Neurologist"],
                "brain": ["Neurologist"],
                "seizure": ["Neurologist"],
                "stroke": ["Neurologist"],
                "migraine": ["Neurologist"],
                
                "bone": ["Orthopedic Surgeon"],
                "joint": ["Orthopedic Surgeon"],
                "knee": ["Orthopedic Surgeon"],
                "back": ["Orthopedic Surgeon"],
                "fracture": ["Orthopedic Surgeon"],
                "shoulder": ["Orthopedic Surgeon"],
                "muscle": ["Orthopedic Surgeon"],
                
                "stomach": ["Gastroenterologist"],
                "belly": ["Gastroenterologist"],
                "digestion": ["Gastroenterologist"],
                "vomit": ["Gastroenterologist"],
                "diarrhea": ["Gastroenterologist"],
                "nausea": ["Gastroenterologist"],
                "acid": ["Gastroenterologist"],
                "bloating": ["Gastroenterologist"],
                
                "cough": ["Pulmonologist"],
                "asthma": ["Pulmonologist"],
                "lung": ["Pulmonologist"],
                "breath": ["Pulmonologist"],
                
                "urine": ["Urologist"],
                "kidney": ["Urologist"],
                "prostate": ["Urologist"],
                
                "pregnant": ["Gynecologist"],
                "pregnancy": ["Gynecologist"],
                "period": ["Gynecologist"],
                "pcos": ["Gynecologist"],
                "gyne": ["Gynecologist"],
                
                "eye": ["Ophthalmologist"],
                "vision": ["Ophthalmologist"],
                "sight": ["Ophthalmologist"],
                
                "depressed": ["Psychiatrist"],
                "anxious": ["Psychiatrist"],
                "stress": ["Psychiatrist"],
                "sad": ["Psychiatrist"],
                "mental": ["Psychiatrist"],
                
                "tooth": ["Dentist"],
                "teeth": ["Dentist"],
                "gum": ["Dentist"],
                
                "diabetes": ["Endocrinologist"],
                "thyroid": ["Endocrinologist"],
                "hormone": ["Endocrinologist"],
                
                "ear": ["ENT Specialist"],
                "throat": ["ENT Specialist"],
                "nose": ["ENT Specialist"],
                "hearing": ["ENT Specialist"],
                "sinus": ["ENT Specialist"]
            }
            
            for broad_key, specs in broad_map.items():
                if broad_key in lower:
                    for s in specs:
                        if s not in matched_specs:
                            matched_specs.append(s)
                            
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
            # Normalize specialization names to match DB values
            if "specializations" in data:
                data["specializations"] = normalize_specializations(data["specializations"])
            return data
        except Exception as e:
            print(f"[WARNING] LLM analysis failed (will retry next request): {e}")
            return None

    # ── Public API ────────────────────────────────────────────────────────────
    async def analyse(self, text: str) -> Dict[str, Any]:
        """Return analysis dict. Always succeeds (falls back to rules)."""
        result = await self._llm_analyse(text)
        if result is None:
            result = self._rule_based(text)
        # Always normalize specializations to match DB values
        result["specializations"] = normalize_specializations(result.get("specializations", []))
        return result

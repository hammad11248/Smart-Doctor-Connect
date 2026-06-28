"""
Smart-Doctor-Connect-AI — AI Agent Service
LangChain-powered chatbot for the AI receptionist feature.
Generates empathetic responses when doctors are offline and collects patient data.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from api.services.recommender import SymptomRecommender


class AIAgent:
    """
    AI receptionist agent that handles patient messages when doctors are unavailable.
    Uses LangChain with Mistral-7B via OpenRouter for response generation.
    Falls back to template-based responses if LLM is unavailable.
    """

    def __init__(self):
        self._llm = None
        self._recommender = SymptomRecommender()

    def _get_llm(self):
        """Return cached LLM instance, or create one. Returns None if API key missing."""
        if self._llm is not None:
            return self._llm
        try:
            from langchain_openai import ChatOpenAI

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return None

            self._llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                model="mistralai/mistral-7b-instruct",
                temperature=0.4,
                max_tokens=512,
                timeout=3.0,
            )
            return self._llm
        except Exception:
            return None

    async def generate_response(
        self,
        patient_name: str,
        message: str,
        doctor_name: str,
        doctor_available: bool,
    ) -> str:
        """
        Generate an AI response to a patient message.
        If doctor is available, direct them to booking.
        If unavailable, generate an empathetic response and collect patient info.
        """
        if doctor_available:
            return (
                f"Great news, {patient_name}! {doctor_name} is currently available. "
                f"You can book an appointment directly using the 'Book Appointment' button "
                f"on their profile. The doctor will see you at your scheduled time."
            )

        # Try LLM response first
        llm_response = await self._llm_respond(patient_name, message, doctor_name)
        if llm_response:
            return llm_response

        # Fallback: template-based response
        return self._template_response(patient_name, message, doctor_name)

    async def _llm_respond(
        self, patient_name: str, message: str, doctor_name: str
    ) -> Optional[str]:
        llm = self._get_llm()
        if llm is None:
            return None

        prompt = f"""You are an AI receptionist for {doctor_name} at Smart-Doctor-Connect-AI Pakistan.
The doctor is currently OFFLINE / unavailable.

Patient "{patient_name}" says: "{message}"

Your tasks:
1. Respond empathetically and professionally in 2-3 sentences.
2. Acknowledge their symptoms/concerns.
3. Let them know that {doctor_name} has been notified via email and will respond soon.
4. If the symptoms sound urgent, advise them to visit the nearest emergency room or call 115.
5. Keep the tone warm, reassuring, and professional.

Respond in plain text only — no JSON, no markdown."""

        try:
            from langchain_core.messages import HumanMessage

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            print(f"[WARNING] AI Agent LLM call failed (will retry next request): {e}")
            return None

    def _template_response(
        self, patient_name: str, message: str, doctor_name: str
    ) -> str:
        """Fallback template response when LLM is unavailable."""
        # Analyse symptoms for urgency
        analysis = self._recommender._rule_based(message)
        urgency = analysis.get("urgency", "LOW")

        if urgency == "EMERGENCY":
            return (
                f"Thank you for reaching out, {patient_name}. Based on your symptoms, "
                f"this appears to be an emergency situation. Please call 115 or visit "
                f"the nearest emergency room immediately. We have also notified "
                f"{doctor_name} about your message and they will follow up with you."
            )
        elif urgency == "HIGH":
            return (
                f"Thank you, {patient_name}. Your symptoms sound concerning. "
                f"{doctor_name} is currently unavailable, but we have sent them an "
                f"email notification with your details. Please seek medical attention "
                f"today if symptoms worsen. The doctor will contact you as soon as possible."
            )
        else:
            return (
                f"Thank you for your message, {patient_name}. {doctor_name} is "
                f"currently unavailable, but don't worry — we've recorded your "
                f"message and notified the doctor via email. They will get back to you "
                f"shortly. In the meantime, please rest and stay hydrated."
            )


# Singleton instance
ai_agent = AIAgent()

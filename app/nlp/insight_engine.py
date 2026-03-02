import json
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def generate_insight(metrics,persona="clinical"):
    persona_instructions = {
        "clinical": "Use a professional clinician tone focusing on utilization patterns relevant to medical decision-making.",
        "executive": "Use a strategic executive tone focused on resource allocation, operational efficiency, growth implications, and cost drivers.",
        "analyst": "Use a neutral data-analyst tone emphasizing statistical interpretation, variance, distribution patterns, and measurable trends."
    }

    prompt = f"""
    You are an AI assistant generating insight summaries for healthcare utilization analytics.

    Persona style to use:
    {persona_instructions[persona]}

    Generate a concise 4–6 sentence executive summary based ONLY on the following metrics.
    You MUST explicitly reference insights from ALL available domains
    (procedures, immunizations, and medications) if present.

    Metrics (JSON-like):
    {json.dumps(metrics, indent=2)}

    Conclude with one sentence summarizing the overall strategic implication.

    RULES:
    - Do NOT speculate beyond the provided metrics
    - Refer only to utilization, demographics, and trends
    - If a metric is weak or missing, acknowledge uncertainty
    - Do NOT hallucinate or invent numbers
    - Tone must match persona

    Return ONLY the narrative paragraph.
    """

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    # Safely extract text
    try:
        return response.text.strip()
    except:
        try:
            return response.candidates[0].content.parts[0].text.strip()
        except:
            return "Unable to generate insight due to response formatting."

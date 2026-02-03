import pandas as pd
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"


# -----------------------------
# UTILITIES
# -----------------------------
def normalize_list(items):
    cleaned = []
    for item in items or []:
        if isinstance(item, dict):
            cleaned.append(" - ".join(str(v) for v in item.values()))
        else:
            cleaned.append(str(item))
    return cleaned


# -----------------------------
# RULE BASED ANALYSIS
# -----------------------------
def rule_based_analysis(row):
    problems, services = [], []

    if str(row.get("website", "")).lower() == "no":
        problems.append("No professional website")
        services.append("Website Development")

    if str(row.get("online_booking", "")).lower() == "no":
        if row.get("category", "") not in ["clothing store", "boutique"]:
            problems.append("Manual appointment handling")
            services.append("Online Booking System")

    if str(row.get("payments", "")).lower() in ["cash", "manual", "no"]:
        problems.append("No digital payment system")
        services.append("Payment Gateway Integration")

    if str(row.get("google_maps", "")).lower() == "no":
        problems.append("Low local discoverability")
        services.append("Local SEO & Google Profile Setup")

    return problems, services


# -----------------------------
# AI ANALYSIS (OLLAMA)
# -----------------------------
def ai_analysis(row):
    prompt = f"""
You are a senior B2B IT consultant assisting an IT services sales team.

Objective:
Identify high-impact IT, automation, and digital system gaps that affect
revenue, efficiency, scalability, or customer experience.

Business details:
- Category: {row.get('category')}
- Website: {row.get('website')}
- Google Maps: {row.get('google_maps')}
- Online Booking: {row.get('online_booking')}
- WhatsApp Available: {row.get('whatsapp')}
- Payments: {row.get('payments')}
- Notes: {row.get('notes')}

Tasks:
1. Identify ONLY IT-related business problems (avoid generic issues).
2. Suggest matching IT services that solve those problems.
3. Suggest realistic automation opportunities.
4. Recommend the BEST contact channel based on business signals.
5. Give ONE short reason why this channel is best.
6. Suggest outreach tone suitable for decision-makers.

Strict Rules:
- Prefer revenue, automation, and scalability problems.
- Use short plain text strings (max 8 words).
- No explanations beyond the required fields.
- Do NOT invent facts or contact details.
- Do NOT return nested objects or arrays of objects.
- Output must ALWAYS be valid JSON.

Contact Channel Logic:
- WhatsApp → if WhatsApp Available = yes AND customer-facing business
- Phone Call → if no website OR no online booking
- Email → if professional services or B2B
- Website Contact Form → if website exists but WhatsApp = no

Priority Score Rules:
- 8–10 → Revenue leakage, heavy manual operations, strong automation fit
- 5–7 → Growth blockers, inefficient systems
- 1–4 → Basic digital improvements

Return ONLY this JSON format:
{
  "problems": ["string"],
  "services": ["string"],
  "automation": ["string"],
  "best_contact_channel": "string",
  "contact_reason": "string",
  "outreach_tone": "string",
  "priority_score": 1
}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        return json.loads(result.get("response", "{}"))

    except Exception:
        return {
            "problems": [],
            "services": [],
            "automation": [],
            "best_contact_channel": "Email",
            "contact_reason": "Fallback default",
            "outreach_tone": "Professional",
            "priority_score": 5
        }


# -----------------------------
# PROCESS MULTI-SHEET EXCEL
# -----------------------------
def process_excel(input_path, output_path):
    sheets = pd.read_excel(input_path, sheet_name=None)
    writer = pd.ExcelWriter(output_path, engine="openpyxl")

    for sheet_name, df in sheets.items():
        print(f"▶ Processing sheet: {sheet_name}")

        if df.empty:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            continue

        # Ensure base columns
        for col in [
            "business_name", "category", "employees", "website",
            "google_maps", "online_booking", "whatsapp",
            "payments", "notes"
        ]:
            if col not in df.columns:
                df[col] = ""

        # Ensure output columns
        for col in [
            "AI_Problems",
            "AI_IT_Services",
            "AI_Automations",
            "AI_Best_Contact_Channel",
            "AI_Contact_Reason",
            "AI_Outreach_Tone",
            "AI_Sales_Priority"
        ]:
            if col not in df.columns:
                df[col] = ""

        for i, row in df.iterrows():
            print(f"   → Row {i+1}/{len(df)}") # type: ignore

            rule_p, rule_s = rule_based_analysis(row)
            ai = ai_analysis(row)

            ai_p = normalize_list(ai.get("problems"))
            ai_s = normalize_list(ai.get("services"))
            ai_a = normalize_list(ai.get("automation"))

            final_problems = list(dict.fromkeys(rule_p + ai_p))
            final_services = list(dict.fromkeys(rule_s + ai_s))

            if not final_problems:
                final_problems = ["Low digital maturity"]
                final_services = ["IT Consultation & Digital Setup"]

            df.at[i, "AI_Problems"] = " | ".join(final_problems) # type: ignore
            df.at[i, "AI_IT_Services"] = " | ".join(final_services) # type: ignore
            df.at[i, "AI_Automations"] = " | ".join(ai_a) # type: ignore
            df.at[i, "AI_Best_Contact_Channel"] = ai.get("best_contact_channel", "Email") # type: ignore
            df.at[i, "AI_Contact_Reason"] = ai.get("contact_reason", "Standard outreach") # type: ignore
            df.at[i, "AI_Outreach_Tone"] = ai.get("outreach_tone", "Professional") # type: ignore
            df.at[i, "AI_Sales_Priority"] = ai.get("priority_score", 5) # type: ignore

        df.to_excel(writer, sheet_name=sheet_name, index=False)

    writer.close()
    print("✅ ALL sheets processed successfully")

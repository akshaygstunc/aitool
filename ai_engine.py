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
# AI ANALYSIS (OLLAMA OPTIMIZED)
# -----------------------------
def ai_analysis(row):
    prompt = f"""
You are an IT sales consultant.

Business details:
- Category: {row.get('category')}
- Website: {row.get('website')}
- Google Maps: {row.get('google_maps')}
- Online Booking: {row.get('online_booking')}
- Payments: {row.get('payments')}
- Notes: {row.get('notes')}

Rules:
1. Identify ONLY IT-related problems.
2. Use short plain text strings.
3. Do NOT return objects or nested data.
4. Always suggest matching IT services.

Return ONLY valid JSON:
{{
  "problems": ["string"],
  "services": ["string"],
  "automation": ["string"],
  "priority_score": 1
}}
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
            "priority_score": 5
        }


# -----------------------------
# PROCESS FULL EXCEL (ALL SHEETS)
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
            "AI_Problems", "AI_IT_Services",
            "AI_Automations", "AI_Sales_Priority"
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

            # HARD FALLBACK (never blank)
            if not final_problems:
                final_problems = ["Low digital maturity"]
                final_services = ["IT Consultation & Digital Setup"]

            df.at[i, "AI_Problems"] = " | ".join(final_problems) # type: ignore
            df.at[i, "AI_IT_Services"] = " | ".join(final_services) # type: ignore
            df.at[i, "AI_Automations"] = " | ".join(ai_a) # type: ignore
            df.at[i, "AI_Sales_Priority"] = ai.get("priority_score", 5) # type: ignore

        df.to_excel(writer, sheet_name=sheet_name, index=False)

    writer.close()
    print("✅ ALL sheets processed successfully")

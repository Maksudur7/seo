import json
import requests
from config import load_config
from modules.site_crawler import load_site_index

class AIEngine:
    def __init__(self, api_key: str = None):
        config = load_config()
        self.api_key = (api_key or config.get("gemini_api_key", "")).strip()

    def analyze_and_draft_reply(self, post_text: str, platform: str = "Social Media"):
        if not self.api_key:
            return {"error": "🔑 Gemini API key setup করা নেই! ড্যাশবোর্ডে গিয়ে সঠিক Gemini API Key দিন।"}

        if not self.api_key.startswith("AIzaSy"):
            return {"error": "❌ আপনার দেওয়া Gemini API Key টি সঠিক নয় (Google Gemini API key 'AIzaSy' দিয়ে শুরু হয়)। অনুগ্রহ করে Google AI Studio থেকে নতুন একটি সঠিক API Key এনে সেভ করুন।"}

        site_pages = load_site_index()
        if not site_pages:
            return {"error": "🌐 ওয়েবসাইট ক্রল করা হয়নি। অনুগ্রহ করে প্রথমে 'Crawl Website Now' বাটনে ক্লিক করুন।"}

        pages_context = []
        for p in site_pages[:15]:
            pages_context.append(f"- Title: {p.get('title')}\n  URL: {p.get('url')}\n  Description: {p.get('description')}")
        
        site_context_str = "\n".join(pages_context)

        system_instruction = f"""
You are an expert Social Media Community Assistant for a file conversion website.
Your task is to analyze user posts from {platform} and determine if the user is looking for a file conversion solution, format help, or digital tool.

Available Tools on Our Website:
{site_context_str}

Rules:
1. Determine if the post expresses a genuine need/interest in file conversion or file editing tools (is_relevant: true/false).
2. If relevant, select the SINGLE BEST matching URL from Our Website Tools list.
3. Draft a helpful, friendly, natural response (max 2-3 sentences). Do NOT sound like spam or an ad. Be genuine and directly solve their query, recommending the matched URL.

Return ONLY a raw JSON object with the following schema:
{{
    "is_relevant": boolean,
    "intent_summary": "brief summary of what user needs",
    "matched_url": "selected website URL",
    "reply_text": "the draft reply message",
    "confidence_score": float (0.0 to 1.0)
}}
"""

        prompt = f"Analyze this post from {platform}:\n\n\"\"\"\n{post_text}\n\"\"\""

        # Try Google GenAI SDK first if installed
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_instruction + "\n\n" + prompt
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            return json.loads(raw_text.strip())

        except Exception as sdk_err:
            print(f"GenAI SDK failed, falling back to REST: {sdk_err}")

        # REST API Fallback across Gemini Pro & Flash models
        endpoints = [
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={self.api_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        ]

        payload = {
            "contents": [{"parts": [{"text": system_instruction + "\n\n" + prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}
        }

        for url in endpoints:
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        if raw_text.startswith("```json"):
                            raw_text = raw_text[7:]
                        if raw_text.startswith("```"):
                            raw_text = raw_text[3:]
                        if raw_text.endswith("```"):
                            raw_text = raw_text[:-3]
                        return json.loads(raw_text.strip())
            except Exception as e:
                print(f"REST endpoint failed for {url[:60]}: {e}")

        return {"error": "Gemini API কলের সময় সমস্যা দেখা দিয়েছে। আপনার দেওয়া Gemini API Key টি সঠিক কিনা আবার যাচাই করুন।"}

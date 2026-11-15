
import os
import random
import sys
import requests

# Configuration
BOT_TOKEN = "8588661665:AAHl2Hwj05-pEA0KHFUD-taZH9dQyVTVwKo"
GEMINI_API_KEY = "AQ.Ab8RN6IHfXyv5E4J57cO-KXcz2UhjbbiOpu2YfGlS8L_GpfL9Q"
OWNER_CHAT_ID = "8190183322"

MODE = os.environ.get("MODE", "draft")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

CHANNEL = "@BethorabyBeth"
FOOTER = "\n\n— @BethorabyBeth"
AMHARIC_CHANCE = 0.2

PERSONA = """
You write Telegram posts for Beth's personal tech channel
"Beth Ora" (@BethorabyBeth).

Beth is a software engineering student learning full-stack
development and building in public.

Voice: warm, honest, curious, encouraging, a bit playful.
Short sentences. Natural student voice.
Never sound like a corporate advertisement or generic motivational poster.

Audience: students, beginner developers, young founders and creators.

RULES:
- Only mention projects, events or achievements appearing in NOTES.
- Never invent statistics, quotes, links or tool features.
- Maximum 900 characters.
- Use 1-4 fitting emojis.
- Use line breaks for readability.
- Use 0-3 hashtags.
- Do not add a channel tag or signature.
- Output ONLY the post text.
"""

SLOTS = {
    "morning": [
        "Write a good-morning post with one small, concrete motivation for a student developer today.",
        "Write a good-morning post with one tiny coding goal and invite readers to share theirs.",
    ],
    "tip": [
        "Share one practical tech tip about Git, debugging, learning habits, VS Code or web development.",
        "Explain one beginner concept simply using a one-line analogy.",
        "Describe one common beginner mistake and how to avoid it.",
    ],
    "build": [
        "Write a build-in-public update based on the NOTES, including one honest struggle.",
        "Share one lesson from the NOTES in a story format: problem, struggle, solution.",
    ],
    "find": [
        "Recommend one genuinely useful free developer tool and explain who it helps.",
        "Suggest a small project a beginner could build this weekend.",
    ],
    "night": [
        "Write a calm goodnight post about progress over perfection, ending with a question.",
        "Ask readers what they learned or built today.",
    ],
}

CRON_TO_SLOT = {
    "0 4 * * *": "morning",
    "30 7 * * *": "tip",
    "0 11 * * *": "build",
    "0 15 * * *": "find",
    "30 18 * * *": "night",
}


def pick_slot(arg):
    arg = (arg or "").strip()
    return arg if arg in SLOTS else CRON_TO_SLOT.get(arg, "tip")


def read_notes():
    try:
        with open("my_notes.md", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "(No notes yet.)"


def generate_post(slot):
    task = random.choice(SLOTS[slot])

    language = (
        "Write mainly in Amharic using Ge'ez script. Keep technical terms in English."
        if random.random() < AMHARIC_CHANCE
        else "Write naturally in English."
    )

    prompt = f"""
NOTES:
{read_notes()}

TASK:
{task}

LANGUAGE:
{language}
"""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent"
    )

    body = {
        "system_instruction": {
            "parts": [{"text": PERSONA}]
        },
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 700,
        },
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            response = requests.post(
                url, json=body, headers=headers, timeout=60
            )
            response.raise_for_status()

            data = response.json()
            candidates = data.get("candidates", [])

            if not candidates:
                raise RuntimeError(f"No Gemini candidates returned: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            post = "".join(
                part.get("text", "") for part in parts
            ).strip()

            if not post:
                raise RuntimeError("Gemini returned an empty post.")

            return post[:900]

        except (requests.RequestException, RuntimeError) as error:
            print(f"Gemini error (attempt {attempt + 1}): {error}")
            if attempt == 1:
                raise

    raise RuntimeError("Gemini failed twice.")


def send(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")

    return result


def main():
    if MODE not in ("draft", "live"):
        raise ValueError("MODE must be 'draft' or 'live'.")

    slot = pick_slot(sys.argv[1] if len(sys.argv) > 1 else "")

    print(f"Generating {slot} post...")

    post = generate_post(slot) + FOOTER

    if MODE == "live":
        send(CHANNEL, post)
        print(f"Successfully posted to {CHANNEL}")

    else:
        send(OWNER_CHAT_ID, f"📝 DRAFT [{slot}]\n\n{post}")
        print("Draft successfully sent to your Telegram.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)

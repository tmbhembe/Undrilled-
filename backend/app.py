import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import azure.cognitiveservices.speech as speechsdk

app = Flask(__name__)
CORS(app)

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "southafricanorth")
TRANSLATOR_ENDPOINT = os.getenv(
    "AZURE_TRANSLATOR_ENDPOINT",
    "https://api.cognitive.microsofttranslator.com"
)

LANGUAGES = {
    "en": "en-US",
    "zu": "zu-ZA",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
}

VOICES = {
    "en": "en-US-AriaNeural",
    "zu": "zu-ZA-ThandoNeural",
}


def require_keys():
    if not SPEECH_KEY or not TRANSLATOR_KEY:
        raise RuntimeError(
            "Azure credentials are missing. Set AZURE_SPEECH_KEY and AZURE_TRANSLATOR_KEY."
        )


def translate_text(text, source_language, target_language):
    url = f"{TRANSLATOR_ENDPOINT.rstrip('/')}/translate"
    params = {
        "api-version": "3.0",
        "from": source_language,
        "to": target_language,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    response = requests.post(
        url,
        params=params,
        headers=headers,
        json=[{"text": text}],
        timeout=30,
    )
    response.raise_for_status()
    return response.json()[0]["translations"][0]["text"]


def synthesize(text, language):
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION,
    )
    speech_config.speech_synthesis_voice_name = VOICES.get(
        language, VOICES["en"]
    )

    result = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None,
    ).speak_text_async(text).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = getattr(result, "cancellation_details", None)
        message = getattr(details, "error_details", "Speech synthesis failed")
        raise RuntimeError(message)

    return result.audio_data


def recognize_audio(file_path, languages):
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION,
    )
    audio_config = speechsdk.audio.AudioConfig(filename=file_path)

    for language in languages:
        speech_config.speech_recognition_language = language
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text, language

    return None, None


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "Undrilled Python backend"})


@app.post("/api/translate")
def api_translate():
    try:
        require_keys()
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        source = data.get("source", "en")
        target = data.get("target", "zu")

        if not text:
            return jsonify({"error": "Text is required."}), 400

        translated = translate_text(text, source, target)
        return jsonify({
            "source_text": text,
            "translated_text": translated,
            "source_language": source,
            "target_language": target,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/interpret")
def api_interpret():
    try:
        require_keys()
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        source = data.get("source", "en")
        target = data.get("target", "zu")
        speak = bool(data.get("speak", True))

        if not text:
            return jsonify({"error": "Text is required."}), 400

        translated = translate_text(text, source, target)
        result = {
            "source_text": text,
            "translated_text": translated,
            "source_language": source,
            "target_language": target,
        }

        if speak:
            audio = synthesize(translated, target)
            result["audio_base64"] = base64.b64encode(audio).decode("ascii")
            result["audio_mime"] = "audio/wav"

        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/transcribe")
def api_transcribe():
    try:
        require_keys()

        if "audio" not in request.files:
            return jsonify({"error": "Upload an audio file using the 'audio' field."}), 400

        languages = request.form.getlist("languages") or [
            "en-US", "zu-ZA", "fr-FR", "de-DE", "es-ES"
        ]

        upload = request.files["audio"]
        suffix = os.path.splitext(upload.filename or "")[1] or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            temp_path = tmp.name

        try:
            text, language = recognize_audio(temp_path, languages)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

        if not text:
            return jsonify({"error": "No speech could be recognized."}), 422

        short_language = next(
            (key for key, value in LANGUAGES.items() if value == language),
            language,
        )
        return jsonify({
            "text": text,
            "language": short_language,
            "language_code": language,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500



SCAM_PATTERNS = [
    ("one time pin", 3), ("otp", 3), ("verification code", 3),
    ("open your banking app", 3), ("confirm the payment", 2),
    ("share your pin", 3), ("read me the code", 3),
    ("account has been compromised", 3), ("account will be blocked", 3),
    ("urgent action", 2), ("fraud department", 2),
    ("verify your account", 2), ("block your card", 2),
    ("click the link", 2), ("remote access", 3),
    ("anydesk", 3), ("teamviewer", 3), ("don't tell anyone", 3),
]

def analyze_scam_text(text):
    lowered = text.lower()
    matches = [(phrase, weight) for phrase, weight in SCAM_PATTERNS if phrase in lowered]
    score = sum(weight for _, weight in matches)
    risk = "high" if score >= 6 else "medium" if score >= 2 else "low"
    return risk, score, [phrase for phrase, _ in matches]


@app.post("/api/security/analyze")
def api_security_analyze():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text is required."}), 400
    risk, score, flags = analyze_scam_text(text)
    return jsonify({
        "risk": risk,
        "score": score,
        "flags": flags,
        "payment_action": "BLOCK" if risk == "high" else "ALLOW_WITH_CAUTION" if risk == "medium" else "ALLOW",
    })


@app.post("/api/chat")
def api_chat():
    try:
        require_keys()
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        language = data.get("language", "en")
        if not message:
            return jsonify({"error": "Message is required."}), 400

        risk, score, flags = analyze_scam_text(message)
        if risk == "high":
            english_reply = (
                "Possible scam detected. Do not send money, share a PIN or verification code, "
                "or follow instructions from the caller. Your payment protection should remain active."
            )
        elif risk == "medium":
            english_reply = (
                "Please be careful. This message contains signs sometimes used in financial scams. "
                "Verify the person using an official number before making a payment."
            )
        else:
            english_reply = (
                "I can help explain banking and security questions. I cannot move money or bypass "
                "your bank's security controls."
            )

        reply = english_reply if language == "en" else translate_text(
            english_reply, "en", language
        )
        return jsonify({
            "reply": reply,
            "risk": risk,
            "score": score,
            "flags": flags,
            "payment_action": "BLOCK" if risk == "high" else "ALLOW_WITH_CAUTION" if risk == "medium" else "ALLOW",
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/")
def root():
    return jsonify({
        "name": "Undrilled Python Backend",
        "status": "running",
        "endpoints": ["/health", "/api/translate", "/api/interpret", "/api/transcribe", "/api/security/analyze", "/api/chat"],
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)

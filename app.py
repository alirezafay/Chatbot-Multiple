from flask import Flask, request, jsonify, render_template
import requests
import json
import os

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

#### Load All User Profiles from Google Drive
def load_all_user_data(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            raise Exception("Invalid JSON format.")
    else:
        raise Exception(f"Failed to download: {response.status_code}")

# Load user data once when app starts
file_id = "YOUR_FILE_ID_HERE"  # <-- Replace this with the new file_id containing both users
all_users_data = load_all_user_data(file_id)

#### Generate Context for Specific User
def build_context(user_profile):
    return f"""
User Profile:
- Name: {user_profile['Personal Information']['name']}
- Age: {user_profile['Personal Information']['age']}
- Occupation: {user_profile['career']['job title']}
- Industry: {user_profile['career']['Current job']}
- Skills: {", ".join(user_profile['career']['skills'])}
- Achievements: {", ".join(user_profile['career']['achievements'])}
- Education Level: {user_profile['Education'].get("Level of education", "N/A")}
- Favorite Topics: {", ".join(user_profile['Preferences'].get("favorite_topics", []))}

Instructions:
- Use this profile when answering any question.
- Respond with personalized insights based on the user's expertise, interests, and achievements.
- Adapt tone and suggestions according to their career and personality.

User Question: INSERT_USER_QUESTION_HERE
"""

#### Send Request to Gemini
def generate_response(user_question, user_id):
    user_profile = all_users_data["users"].get(user_id)
    if not user_profile:
        return f"Error: User ID '{user_id}' not found."

    prompt = build_context(user_profile).replace("INSERT_USER_QUESTION_HERE", user_question)

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(URL, json=payload, headers=headers)
    if "candidates" in response.json():
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return "Error: No AI response received."

#### Routes
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_question = data.get("question")
    user_id = data.get("user_id")  # e.g., 'user_ahmad' or 'user_sara'

    if not user_question or not user_id:
        return jsonify({"response": "Missing question or user ID."}), 400

    response = generate_response(user_question, user_id)
    return jsonify({"response": response})

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

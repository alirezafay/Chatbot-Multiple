from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



API_KEY = os.environ.get("API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<ChatHistory {self.id} {self.user_id} {self.role}>'

with app.app_context():
    db.create_all() 
    
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

file_id = "1DiIYwGARYQGxPXpEWgugr6RNyu1c48tC"  # Replace with your own Google Drive file ID
all_users_data = load_all_user_data(file_id)

def build_context(user_profile):
    return f"""
User Profile:
- Name: {user_profile['Personal Information']['name']}
- Age: {user_profile['Personal Information']['age']}
- Sex: {user_profile['Personal Information']['sex']}
- Location: {user_profile['Personal Information']['habitat']}

Career:
- Job Title: {user_profile['career']['job title']}
- Current Role: {user_profile['career']['Current job']}
- First Work Experience: {user_profile['career']['first work experience']}
- Skills: {", ".join(user_profile['career']['skills'])}
- Achievements: {", ".join(user_profile['career']['achievements'])}

Education:
- Level of Education: {user_profile['Education'].get('Level of education', 'N/A')}
- Special Programs: {", ".join(user_profile['Education'].get('Special educational programs', []))}
- University Success: {user_profile['Education'].get('Significant academic experience', 'N/A')}
- Courses with High Performance: {", ".join(user_profile['Education'].get('University courses with good performance', []))}
- Awards & Scholarships: {user_profile['Education'].get('Awards and Scholarships', 'N/A')}

Personal Achievements:
- Sports Achievement: {user_profile['Personal Achievements'].get('Significant sport achievement', 'N/A')}
- Overcome Obstacles: {user_profile['Personal Achievements'].get('an overcame obstacle', 'N/A')}

Major Life Events:
- Moved Cities: {user_profile['major changes in life'].get('moving to a new city', 'N/A')}
- Relationships: {user_profile['major changes in life'].get('relationships', 'N/A')}
- Family Changes: {user_profile['major changes in life'].get('family changes', 'N/A')}
- Retirement: {user_profile['major changes in life'].get('retirement', 'N/A')}
- Most Important Life Experience: {user_profile['major changes in life'].get('most important life experience', 'N/A')}

Preferences:
- Music: {", ".join(user_profile['Preferences'].get('music', []))}
- Movies: {", ".join(user_profile['Preferences'].get('movies', []))}
- Favorite Topics: {", ".join(user_profile['Preferences'].get('favorite_topics', []))}

Travel Experience:
- First Foreign Trip: {user_profile['Travel Experience'].get('First foreign travel experience', 'N/A')}
- Most Valuable Trip: {user_profile['Travel Experience'].get('the most valuable travel experience', 'N/A')}
- Cultural Exchange: {user_profile['Travel Experience'].get('cultural exchange', 'N/A')}

Social Impact:
- Volunteer Work: {user_profile['Social Impact'].get('Volunteer work', 'N/A')}
- Social Events: {", ".join(user_profile['Social Impact'].get('Social event', []))}
- Social Movements: {user_profile['Social Impact'].get('Attending a social movement', 'N/A')}

Cognitive Traits:
- IQ: {user_profile['Intelligence'].get('IQ', 'N/A')}
- EQ: {user_profile['Intelligence'].get('EQ', 'N/A')}

Instructions:
- Use this detailed profile to provide responses that are tailored and empathetic.
- Reflect the user’s professional background, personal journey, values, and personality in your answers.
- Prioritize clarity and relevance in advice, referencing their education, experiences, or preferences as needed.
- When applicable, consider location and culture in the context of recommendations or examples.

User Question: INSERT_USER_QUESTION_HERE
"""

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_question = data.get("question")
    user_id = data.get("user_id")

    if not user_question or not user_id:
        return jsonify({"response": "Missing question or user ID."}), 400

    db.session.add(ChatHistory(user_id=user_id, role='user', message=user_question))
    db.session.commit()

    response_text = generate_response(user_question, user_id)
    db.session.add(ChatHistory(user_id=user_id, role='bot', message=response_text))
    db.session.commit()

    return jsonify({"response": response_text})

@app.route("/history", methods=["POST"])
def get_history():
    data = request.json
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"history": []})

    messages = ChatHistory.query.filter_by(user_id=user_id).all()
    history = [{"role": msg.role, "content": msg.message} for msg in messages]
    return jsonify({"history": history})

@app.route("/clear_history", methods=["POST"])
def clear_history():
    data = request.json
    user_id = data.get("user_id")
    if user_id:
        ChatHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({"message": "Chat history cleared."})
    return jsonify({"error": "No user_id provided."}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from runnables import CrisisRunnable, EmotionSelectorRunnable, SummaryRunnable, ReappraisalRunnable, handle_summary_confirmation
import os
from dotenv import load_dotenv
from urllib.parse import parse_qs
import secrets

# I am constantly feeling overwhelmed at work because of the high expectations and the pressure to perform. This has been affecting my mental health and causing me stress every day.


load_dotenv()


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://nathanpaek:postgres@localhost:5432/reappraisal_bot'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Conversations(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)

    value1 = db.Column(db.String())
    value2 = db.Column(db.String())
    value3 = db.Column(db.String())
    value4 = db.Column(db.String())
    value5 = db.Column(db.String())
    value6 = db.Column(db.String())
    value7 = db.Column(db.String())
    value8 = db.Column(db.String())
    value9 = db.Column(db.String())
    value10 = db.Column(db.String())
    value11 = db.Column(db.String())
    value12 = db.Column(db.String())
    value13 = db.Column(db.String())
    value14 = db.Column(db.String())
    value15 = db.Column(db.String())

    issue = db.Column(db.String())
    issue_summary = db.Column(db.String())
    
    emotion1 = db.Column(db.String())
    emotion2 = db.Column(db.String())
    emotion3 = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime)

    def __init__(self):
        parsed_data = parse_qs(request.query_string)
        parsed_values = {key: value[0] if value else None for key, value in parsed_data.items()}
        self.value1 = parsed_values['value1']
        self.value2 = parsed_values['value2']
        self.value3 = parsed_values['value3']
        self.value4 = parsed_values['value4']
        self.value5 = parsed_values['value5']
        self.value6 = parsed_values['value6']
        self.value7 = parsed_values['value7']
        self.value8 = parsed_values['value8']
        self.value9 = parsed_values['value9']
        self.value10 = parsed_values['value10']
        self.value11 = parsed_values['value11']
        self.value12 = parsed_values['value12']
        self.value13 = parsed_values['value13']
        self.value14 = parsed_values['value14']
        self.value15 = parsed_values['value15']


class Messages(db.Model):
    __tablename__ = 'messages'

    msg_id = db.Column(db.Integer, primary_key=True)
    convo_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sent_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(), nullable=False)
    message = db.Column(db.Text(), nullable=False)

    conversation = db.relationship('Conversations', backref=db.backref('messages', lazy=True, cascade="all, delete-orphan"))

    def __init__(self, convo_id, source, message):
        self.convo_id = convo_id
        self.source = source
        self.message = message


llm = ChatOpenAI( 
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=256,
    api_key=os.environ["OPENAI_API_KEY"],
)
crisis_runnable = CrisisRunnable(model=llm)
summary_runnable = SummaryRunnable(model=llm)
reappraisal_runnable = ReappraisalRunnable(model=llm)
chat_history = InMemoryChatMessageHistory()


@app.route('/')
def index():
    # parsed_data = parse_qs(request.query_string)
    # parsed_values = {key: value[0] if value else None for key, value in parsed_data.items()}
    # session['parsed_values'] = parsed_values
    session['parsed_values'] = {'value1': 'patriotism', 'value2': 'patience'}
    return send_from_directory('templates', 'index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    action = data.get('action', '')
    emotion_index = data.get('emotion_index', 0)

    if action == 'start':
        issue = data.get('user_input', '')
        session['issue'] = issue
        chat_history.add_user_message(issue)
        crisis_check = crisis_runnable(issue)
        if crisis_check == "::crisis::":
            return jsonify({"message": "crisis."}), 200
        return jsonify({"message": "emotion wheel. please choose three emotions"}), 200

    if action == 'select_emotions':
        emotion_selector = EmotionSelectorRunnable(crisis_runnable)
        selected_emotions = emotion_selector(data)
        if selected_emotions == "::crisis::":
            return jsonify({"message": "crisis detected"}), 200

        chat_history.add_user_message(data.get("user_input", ""))

        session['selected_emotions'] = selected_emotions
        session['emotions_data'] = {}
        session['current_emotion_index'] = 0

        return jsonify({"message": f"why are you feeling {selected_emotions[0]}?", "emotion_index": 0}), 200


    elif action == 'provide_reason':
        selected_emotions = session.get('selected_emotions', [])
        emotions_data = session.get('emotions_data', {})
        current_emotion_index = session.get('current_emotion_index', 0)
        
        current_emotion = selected_emotions[current_emotion_index]
        reason = data.get('user_input', '')
        chat_history.add_user_message(reason)
        emotions_data[current_emotion] = reason
        
        session['emotions_data'] = emotions_data
        
        current_emotion_index += 1
        session['current_emotion_index'] = current_emotion_index

        if current_emotion_index < len(selected_emotions):
            next_emotion = selected_emotions[current_emotion_index]
            return jsonify({"message": f"why are you feeling {next_emotion}?", "emotion_index": current_emotion_index}), 200
        else:
            input_data = {
                "issue": session.get("issue", ""),
                "emotions": selected_emotions,
                "emotions_data": emotions_data
            }
            print(input_data)
            summary = summary_runnable(input_data)
            session['summary'] = summary
            chat_history.add_ai_message(summary)
            
            return jsonify({"summary": summary, "message": "does this summary adequately capture how you're feeling? (yes/no)"}), 200

    elif action == 'confirm_summary':
        user_selection = data.get('user_selection', '').strip().lower()
        if user_selection not in ['yes', 'no']:
            return jsonify({"message": "Please enter 'yes' or 'no'."}), 400
        
        if user_selection == 'yes':
            return generate_reappraisals()
        else:
            return jsonify({"message": "I see. Could you please provide more details or corrections?", "next_action": "edit_summary"}), 200

    elif action == 'submit_ratings':
        ratings = data.get('ratings', [])
        # Process the ratings as needed
        return jsonify({
            "message": "Thank you for your ratings. Is there anything else you'd like to discuss?",
            "next_action": "final_step"
        }), 200

    else:
        return jsonify({"message": "Invalid action specified."}), 400


def generate_reappraisals():
    final_summary = session.get('summary', '')
    value1 = session['parsed_values'].get('value1', '')
    value15 = session['parsed_values'].get('value15', '')

    reappraisal1 = reappraisal_runnable({
        "issue": final_summary,
        "value": value1
    })

    reappraisal15 = reappraisal_runnable({
        "issue": final_summary,
        "value": value15
    })

    return jsonify({
        "message": "Here are two reappraisals based on your values. Please rate how helpful each one is on a scale from 0 to 10.",
        "reappraisals": [
            {"value": value1, "text": reappraisal1},
            {"value": value15, "text": reappraisal15}
        ],
        "next_action": "rate_reappraisals"
    }), 200


if __name__ == '__main__':
    app.run(debug=True)

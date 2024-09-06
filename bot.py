from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableMap, RunnablePassthrough
from langchain_core.chat_history import InMemoryChatMessageHistory
from runnables import CrisisRunnable, EmotionSelectorRunnable, SummaryRunnable, ReappraisalRunnable, handle_summary_confirmation
import os
from dotenv import load_dotenv
from urllib.parse import parse_qs
import secrets
import random
import json

# I am constantly feeling overwhelmed at work because of the high expectations and the pressure to perform. This has been affecting my mental health and causing me stress every day.


load_dotenv()


app = Flask(__name__, static_url_path='/static')
app.secret_key = os.environ["SECRET_KEY"]
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://nathanpaek:vbriscool@db:5432/reappraisal_bot'


# 'postgresql://nathanpaek:postgres@localhost:5432/reappraisal_bot'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Conversations(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    v1 = db.Column(db.String())
    v2 = db.Column(db.String())
    v3 = db.Column(db.String())
    v4 = db.Column(db.String())
    v5 = db.Column(db.String())
    v6 = db.Column(db.String())
    v7 = db.Column(db.String())
    v8 = db.Column(db.String())
    v9 = db.Column(db.String())
    v10 = db.Column(db.String())
    v11 = db.Column(db.String())
    v12 = db.Column(db.String())
    v13 = db.Column(db.String())
    v14 = db.Column(db.String())
    v15 = db.Column(db.String())
    v16 = db.Column(db.String())

    issue = db.Column(db.String())
    issue_summary = db.Column(db.String())
    
    emotion1 = db.Column(db.String())
    emotion2 = db.Column(db.String())
    emotion3 = db.Column(db.String())

    reason1 = db.Column(db.String())
    reason2 = db.Column(db.String())
    reason3 = db.Column(db.String())

    reappraisal_high = db.Column(db.String())
    reappraisal_low = db.Column(db.String())
    reappraisal_general = db.Column(db.String())

    reappraisal_high_value = db.Column(db.String())
    reappraisal_low_value = db.Column(db.String())
    reappraisal_general_value = db.Column(db.String())

    r1q1 = db.Column(db.String())
    r1q2 = db.Column(db.String())

    r2q1 = db.Column(db.String())
    r2q2 = db.Column(db.String())

    r3q1 = db.Column(db.String())
    r3q2 = db.Column(db.String())

    crisis_input = db.Column(db.String()) # ADD THIS FUNCTIONALITY

    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, parsed_values):
        self.v1 = parsed_values['v1']
        self.v2 = parsed_values['v2']
        self.v3 = parsed_values['v3']
        self.v4 = parsed_values['v4']
        self.v5 = parsed_values['v5']
        self.v6 = parsed_values['v6']
        self.v7 = parsed_values['v7']
        self.v8 = parsed_values['v8']
        self.v9 = parsed_values['v9']
        self.v10 = parsed_values['v10']
        self.v11 = parsed_values['v11']
        self.v12 = parsed_values['v12']
        self.v13 = parsed_values['v13']
        self.v14 = parsed_values['v14']
        self.v15 = parsed_values['v15']
        self.v16 = parsed_values['v16']



class Messages(db.Model):
    __tablename__ = 'messages'

    msg_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    max_tokens=512,
    api_key=os.environ["OPENAI_API_KEY"],
)
crisis_runnable = CrisisRunnable(model=llm)
summary_runnable = SummaryRunnable(model=llm)
reappraisal_runnable = ReappraisalRunnable(model=llm)
chat_history = InMemoryChatMessageHistory()

value_mapping = {'v1': 'financial success through artistic/creative expression',
        'v2': 'entrepreneurial independence and self-sufficiency',
        'v3': 'financial stability',
        'v4': 'alignment of career with personal passions and values',
        'v5': 'excellence and dedication in professional endeavors',
        'v6': 'flexibility and adaptability in career choices and environments',
        'v7': 'the importance of work-life balance and prioritizing family and personal well-being over career ambitions',
        'v8': 'ethical conduct',
        'v9': 'reliability',
        'v10': 'career advancement and professional growth',
        'v11': 'mentorship and supportive leadership',
        'v12': 'fulfillment through meaningful pursuits, meaningful work and the impact of helping others',
        'v13': 'education, continuous personal and professional growth through education and skill development',
        'v14': 'autonomy in professional life and decision-making., Creativity and autonomy in professional pursuits',
        'v15': 'recognition and respect in professional accomplishments, achievement and recognition in professional pursuits',
        'v16': 'meaningful work and the impact of helping others, helping others'}


@app.route('/')
def index():

    # Hardcoded values
    # key is v1 v2
    # value is score

    # PARSE QUERY STRING HERE
    parsed_data = parse_qs(request.query_string.decode('utf-8'))
    parsed_values = {key: int(value[0]) if value else None for key, value in parsed_data.items()}
    session['parsed_values'] = parsed_values
   
    session['reappraisal_count'] = 0 # how many reappraisals shown to user
    return send_from_directory('templates', 'index.html')


@app.route('/chat', methods=['POST'])
def chat():
    print("RECEIVED CHAT REQUEST")
    """session['parsed_values'] = {
        'v1': 2,
        'v2': 4,
        'v3': 8,
        'v4': 9,
        'v5': 13,
        'v6': 5,
        'v7': 1,
        'v8': 15,
        'v9': 6,
        'v10': 12,
        'v11': 14,
        'v12': 3,
        'v13': 10,
        'v14': 7,
        'v15': 11,
        'v16': 16
    }
    session['reappraisal_count'] = 0"""
    # session['convo_id'] = None

    # MAKE SURE INDEX ROUTE COMES BEFORE CHAT ROUTE
    #if 'parsed_values' not in session:
    #    return redirect(url_for('index'))


    data = request.json

    print(f"REQUEST DATA: {data}")

    action = data.get('action', '')
    emotion_index = data.get('emotion_index', 0)
    
    crisis_message = """We are sorry, but this issue is outside of the capabilities of our reappraisal engine. If you are experiencing thoughts of harming yourself, you may reach out to the 24-hour confidential suicide prevention hotline by dialing 988.
    <a href="...">988 Suicide and Crisis Lifeline</a>

    You may also text HOME to 741741 to connect to a volunteer crisis counselor by text message.
    <a href="...">https://www.crisistextline.org/</a>

    """


    if action == 'start':
        issue = data.get('user_input', '')
        session['issue'] = issue
        chat_history.add_user_message(issue)


        ##### DATABASE #####

        conversation = Conversations(session['parsed_values'])
        db.session.add(conversation)
        db.session.commit()
        session['convo_id'] = conversation.id
        with open ('myfile.json', 'w') as json_file:
            json.dump(session, json_file)
        conversation.issue = issue

        user_message = Messages(convo_id=conversation.id, source='human', message=issue)
        db.session.add(user_message)
        db.session.commit()

        ##### DATABASE #####


        runnable = RunnableMap({
            "crisis_check": crisis_runnable,
            "issue": RunnablePassthrough()
        })
        result = runnable.invoke(issue)
        if result["crisis_check"] == "::crisis::":
            ##### DATABASE #####
            conversation.crisis_input = issue
            db.session.commit()
            ##### DATABASE #####
            return jsonify({"message": "crisis detected", "crisis_message": crisis_message, "next_action": "final_step"}), 200
        return jsonify({"message": "Choose up to three emotions that best describe how you're feeling."}), 200


    if action == 'select_emotions':
        """ emotion_selector = EmotionSelectorRunnable(crisis_runnable)
        selected_emotions = emotion_selector(data)
        if selected_emotions == "::crisis::":
            return jsonify({"message": "crisis detected"}), 200
        chat_history.add_user_message(data.get("user_input", "")) """

        selected_emotions = data.get('selected_emotions', [])
        
        ##### DATABASE #####

        # emotion_message = Messages(convo_id=session['convo_id'], source='human', message=data.get("user_input", ""))
        # db.session.add(emotion_message)
        # db.session.commit()

        ##### DATABASE #####

        print(selected_emotions)

        session['selected_emotions'] = selected_emotions
        session['emotions_data'] = {}
        session['current_emotion_index'] = 0

        return jsonify({"message": f"What makes you feel {selected_emotions[0]}?", "emotion_index": 0}), 200
        # return jsonify({"message": f"Why are you feeling {', '.join(selected_emotions)}?"}), 200


    elif action == 'provide_reason':
        with open ('myfile.json', 'w') as json_file:
            json.dump(session, json_file)
        conversation = Conversations.query.get(session['convo_id'])

        selected_emotions = session.get('selected_emotions', [])
        emotions_data = session.get('emotions_data', {})
        current_emotion_index = session.get('current_emotion_index', 0)
        
        current_emotion = selected_emotions[current_emotion_index]
        reason = data.get('user_input', '')
        runnable = RunnableMap({
            "crisis_check": crisis_runnable,
            "user_input": RunnablePassthrough()
        })
        result = runnable.invoke(reason)
        if result["crisis_check"] == "::crisis::":
            ##### DATABASE #####
            conversation.crisis_input = reason
            db.session.commit()
            ##### DATABASE #####
            print("CRISIS")
            return jsonify({"message": "crisis detected", "crisis_message": crisis_message, "next_action": "final_step"}), 200


        ##### DATABASE #####

        # conversation = Conversations.query.get(session['convo_id'])
        if (current_emotion_index == 0):
            conversation.emotion1 = current_emotion
            conversation.reason1 = reason
        elif (current_emotion_index == 1):
            conversation.emotion2 = current_emotion
            conversation.reason2 = reason
        elif (current_emotion_index == 2):
            conversation.emotion3 = current_emotion
            conversation.reason3 = reason
        db.session.commit()

        ##### DATABASE #####

        
        chat_history.add_user_message(reason)
        emotions_data[current_emotion] = reason
        
        session['emotions_data'] = emotions_data
        
        current_emotion_index += 1
        session['current_emotion_index'] = current_emotion_index


        ##### DATABASE #####

        reason_message = Messages(convo_id=session['convo_id'], source='human', message=reason)
        db.session.add(reason_message)
        db.session.commit()

        ##### DATABASE #####


        if current_emotion_index < len(selected_emotions):
            print(f"CURRENT EMOTIONS INDEX: {current_emotion_index}")
            next_emotion = selected_emotions[current_emotion_index]
            return jsonify({"message": f"What makes you feel {next_emotion}?", "emotion_index": current_emotion_index}), 200
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


            ##### DATABASE #####

            summary_message = Messages(convo_id=session['convo_id'], source='AI', message=summary)
            db.session.add(summary_message)
            db.session.commit()

            ##### DATABASE #####
            

            return jsonify({"summary": summary, "message": "does this summary adequately capture how you're feeling? (yes/no)"}), 200


    elif action == 'confirm_summary':
        user_selection = data.get('user_selection', '').strip().lower()
        #if user_selection not in ['yes', 'no']:
            #return jsonify({"message": "Please enter 'yes' or 'no'."}), 400
            

        ##### DATABASE #####

        confirmation_message = Messages(convo_id=session['convo_id'], source='human', message=user_selection)
        db.session.add(confirmation_message)
        db.session.commit()

        ##### DATABASE #####


        if user_selection == 'yes':


            ##### DATABASE #####

            conversation = Conversations.query.get(session['convo_id'])
            conversation.issue_summary = session['summary']
            db.session.commit()

            ##### DATABASE #####


            # session['reappraisal_number'] = 1

            return generate_reappraisals()
        else:

            return jsonify({"message": "Please edit the summary below:", "next_action": "edit_summary", "summary": session['summary'].split("Does this summary adequately", 1)[0]}), 200

    elif action == 'edit_summary':
        edited_summary = data.get('user_input', '').strip()
        conversation = Conversations.query.get(session['convo_id'])
        runnable = RunnableMap({
            "crisis_check": crisis_runnable,
            "edited_summary": RunnablePassthrough()
        })
        result = runnable.invoke(edited_summary)
        if result["crisis_check"] == "::crisis::":
            ##### DATABASE #####
            conversation.crisis_input = edited_summary
            db.session.commit()
            ##### DATABASE #####
            return jsonify({"message": "crisis detected", "crisis_message": crisis_message, "next_action": "final_step"}), 200
        session['summary'] = edited_summary
        chat_history.add_user_message(edited_summary)


        ##### DATABASE #####

        # conversation = Conversations.query.get(session['convo_id'])
        conversation.issue_summary = edited_summary
        db.session.commit()

        ##### DATABASE #####

        reappraisal_response = generate_reappraisals()
        return reappraisal_response

    elif action == 'rate_reappraisal':
        print('RATE REAPPRAISAL HIT')
        reappraisal_count = session.get('reappraisal_count', 0)
        reappraisal_order = session.get('reappraisal_order', [])
        
        if reappraisal_count >= len(reappraisal_order):
            return jsonify({"message": "Thanks for chatting! I hope that the reappraisals helped.", "next_action": "final_step"}), 200

        reappraisal_number = reappraisal_order[reappraisal_count]
        effectiveness_rating = data.get('effectiveness_rating', '')
        believability_rating = data.get('believability_rating', '')

        ##### DATABASE #####
        conversation = Conversations.query.get(session['convo_id'])
        setattr(conversation, f'r{reappraisal_number}q1', effectiveness_rating)
        setattr(conversation, f'r{reappraisal_number}q2', believability_rating)
        db.session.commit()
        ##### DATABASE #####

        session['reappraisal_count'] = reappraisal_count + 1

        if reappraisal_count < 2: 
            return generate_reappraisals()
        else:
            return jsonify({"message": "Thanks for chatting! I hope that the reappraisals helped.", "next_action": "final_step"}), 200
    else:
        return jsonify({"message": "Invalid action specified."}), 400


def generate_reappraisals():
    print("GENERATE REAPPRAISALS FUNCTION HIT")
    final_summary = session.get('summary', '')
    print("FINAL SUMMARY")
    reappraisal_count = session.get('reappraisal_count', 0)
    print(f'REAPPRAISAL COUNT: {reappraisal_count}')
    if reappraisal_count == 0:
        reappraisal_order = random.sample([1, 2, 3], 3)
        print(reappraisal_order)
        session['reappraisal_order'] = reappraisal_order
        session['reappraisal_count'] = 0
    else:
        reappraisal_order = session.get('reappraisal_order', [])

    if reappraisal_count >= 3:
        return jsonify({"message": "Thanks for chatting! I hope that the reappraisals helped.", "next_action": "final_step"}), 200

    reappraisal_number = reappraisal_order[reappraisal_count]

    if reappraisal_number == 1:
        min_key = min(session['parsed_values'], key=session['parsed_values'].get)
        value = value_mapping.get(min_key, "")
    elif reappraisal_number == 2:
        max_key = max(session['parsed_values'], key=session['parsed_values'].get)
        value = value_mapping.get(max_key, "")
    elif reappraisal_number == 3:
        value = ""  # VALUE AGNOSTIC
    
    reappraisal = reappraisal_runnable({
        "issue": final_summary,
        "value": value
    })

    ##### DATABASE #####
    conversation = Conversations.query.get(session['convo_id'])
    if reappraisal_number == 1:
        conversation.reappraisal_high = reappraisal
        conversation.reappraisal_high_value = value
    elif reappraisal_number == 2:
        conversation.reappraisal_low = reappraisal
        conversation.reappraisal_low_value = value
    elif reappraisal_number == 3:
        conversation.reappraisal_general = reappraisal
        conversation.reappraisal_general_value = value
    db.session.commit()
    ##### DATABASE #####

    # session['reappraisal_count'] = reappraisal_count + 1

    if reappraisal_count == 0:
        disclaimer = "I will now give you three reappraisals. Disclaimer: These alternate perspectives were generated by an artificial intelligence bot powered by GPT-4. We cannot guarantee that these perspectives are helpful or true perspectives and we encourage you to use your own judgement before accepting any alternate perspective offered in the course of this study."
    else:
        disclaimer = None

    return jsonify({
        "disclaimer": disclaimer,
        "message": f"Reappraisal {reappraisal_count + 1} of 3: {reappraisal}",
        "reappraisal_number": reappraisal_number,
        "reappraisal_count": reappraisal_count + 1,
        "next_action": "rate_reappraisal"
    }), 200


if __name__ == '__main__':

    app.run(debug=True)

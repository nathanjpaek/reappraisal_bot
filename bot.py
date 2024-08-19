from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_from_directory
from runnables import CrisisRunnable, EmotionSelectorRunnable, SummaryRunnable, handle_summary_confirmation
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import InMemoryChatMessageHistory
import os
from dotenv import load_dotenv
import secrets


load_dotenv()


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=256,
    api_key=os.environ["OPENAI_API_KEY"],
)
crisis_runnable = CrisisRunnable(model=llm)
summary_runnable = SummaryRunnable(model=llm)
chat_history = InMemoryChatMessageHistory()


@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    action = data.get('action', '')
    emotion_index = data.get('emotion_index', 0)

    if action == 'start':
        issue = data.get('user_input', '')
        chat_history.add_user_message(issue)
        crisis_check = crisis_runnable(issue)
        if crisis_check == "::crisis::":
            return jsonify({"message": "crisis."}), 200
        return jsonify({"message": "emotion wheel. please write down your emotions"}), 200

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
            summary = summary_runnable(input_data)
            chat_history.add_ai_message(summary)
            
            return jsonify({"summary": summary, "message": "does this summary adequately capture how you're feeling? (yes/no)"}), 200


    elif action == 'confirm_summary':
        confirmation, final_summary = handle_summary_confirmation(data)
        
        # if confirmation == "invalid":
            # return jsonify({"message": "invalid"}), 400
        
        chat_history.add_user_message(data.get("user_selection", ""))
        chat_history.add_ai_message(final_summary)
        
        return jsonify({"confirmation": confirmation, "final_summary": final_summary}), 200

    else:
        return jsonify({"message": "Invalid action specified."}), 400


if __name__ == '__main__':
    app.run(debug=True)

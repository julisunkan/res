from flask import Blueprint, request, jsonify
from utils.ai_engine import chat_with_career_assistant

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/message', methods=['POST'])
def send_message():
    data = request.get_json(silent=True) or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'messages are required'}), 400
    try:
        response = chat_with_career_assistant(messages)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

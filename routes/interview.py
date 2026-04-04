import json
from flask import Blueprint, request, jsonify
from utils.ai_engine import generate_interview_questions

interview_bp = Blueprint('interview', __name__)


@interview_bp.route('/generate', methods=['POST'])
def generate_questions():
    data = request.get_json()
    job_description = data.get('job_description', '')
    if not job_description:
        return jsonify({'error': 'job_description is required'}), 400
    try:
        raw = generate_interview_questions(job_description)
        raw = raw.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0] if '```' in raw else raw
        questions = json.loads(raw)
        return jsonify({'questions': questions})
    except Exception as e:
        return jsonify({'error': str(e), 'raw': raw if 'raw' in dir() else ''}), 500

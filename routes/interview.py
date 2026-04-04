from flask import Blueprint, request, jsonify
from utils.ai_engine import generate_interview_questions
from utils.analyzer import parse_json_safely

interview_bp = Blueprint('interview', __name__)


@interview_bp.route('/generate', methods=['POST'])
def generate_questions():
    data = request.get_json(silent=True) or {}
    job_description = data.get('job_description', '').strip()
    if not job_description:
        return jsonify({'error': 'job_description is required'}), 400
    raw = ''
    try:
        raw = generate_interview_questions(job_description)
        questions = parse_json_safely(raw)
        if not isinstance(questions, list):
            raise ValueError('AI did not return a valid list of questions')
        # Ensure each item has required keys
        cleaned = []
        for q in questions:
            if isinstance(q, dict) and 'question' in q:
                cleaned.append({
                    'question': q.get('question', ''),
                    'sample_answer': q.get('sample_answer', q.get('answer', 'No sample answer provided.')),
                })
        return jsonify({'questions': cleaned})
    except Exception as e:
        return jsonify({'error': str(e), 'raw': raw[:500] if raw else ''}), 500

import json
from flask import Blueprint, request, jsonify
from utils.ai_engine import optimize_linkedin_profile

linkedin_bp = Blueprint('linkedin', __name__)


@linkedin_bp.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    headline = data.get('headline', '')
    about = data.get('about', '')
    job_title = data.get('job_title', '')
    industry = data.get('industry', '')
    if not headline and not about:
        return jsonify({'error': 'headline or about is required'}), 400
    try:
        raw = optimize_linkedin_profile(headline, about, job_title, industry)
        raw = raw.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw
            raw = raw.rsplit('```', 1)[0] if '```' in raw else raw
        result = json.loads(raw)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

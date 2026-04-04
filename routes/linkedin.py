from flask import Blueprint, request, jsonify
from utils.ai_engine import optimize_linkedin_profile
from utils.analyzer import parse_json_safely

linkedin_bp = Blueprint('linkedin', __name__)


@linkedin_bp.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json(silent=True) or {}
    headline = data.get('headline', '').strip()
    about = data.get('about', '').strip()
    job_title = data.get('job_title', '').strip()
    industry = data.get('industry', '').strip()
    if not headline and not about:
        return jsonify({'error': 'headline or about section is required'}), 400
    raw = ''
    try:
        raw = optimize_linkedin_profile(headline, about, job_title, industry)
        result = parse_json_safely(raw)
        if not isinstance(result, dict):
            raise ValueError('AI did not return valid JSON')
        return jsonify({
            'headline': result.get('headline', headline),
            'about': result.get('about', about),
        })
    except Exception as e:
        return jsonify({'error': str(e), 'raw': raw[:500] if raw else ''}), 500

import json
import re
from utils.ai_engine import analyze_match, analyze_job_description


def parse_json_safely(text):
    try:
        text = text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        return json.loads(text)
    except Exception:
        return None


def get_match_analysis(resume_text, job_description):
    raw = analyze_match(resume_text, job_description)
    data = parse_json_safely(raw)
    if data and isinstance(data, dict):
        return {
            'score': float(data.get('score', 0)),
            'missing_keywords': data.get('missing_keywords', []),
            'suggestions': data.get('suggestions', []),
        }
    return {
        'score': 0,
        'missing_keywords': [],
        'suggestions': ['Could not parse analysis. Please try again.'],
        'raw': raw
    }


def get_job_analysis(job_description):
    raw = analyze_job_description(job_description)
    data = parse_json_safely(raw)
    if data and isinstance(data, dict):
        return {
            'required_skills': data.get('required_skills', []),
            'keywords': data.get('keywords', []),
            'experience_level': data.get('experience_level', 'Not specified'),
            'key_responsibilities': data.get('key_responsibilities', []),
        }
    return {
        'required_skills': [],
        'keywords': [],
        'experience_level': 'Not specified',
        'key_responsibilities': [],
        'raw': raw
    }

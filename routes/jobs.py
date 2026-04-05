from flask import Blueprint, request, jsonify, abort
from utils.data_layer import (
    job_list, job_get, job_create, job_update, job_delete,
    job_count, job_count_by_status,
)
from utils.analyzer import get_job_analysis

jobs_bp = Blueprint('jobs', __name__)

VALID_STATUSES = {'Applied', 'Interview', 'Offer', 'Rejected'}


@jobs_bp.route('/', methods=['GET'])
def list_jobs():
    return jsonify(job_list())


@jobs_bp.route('/', methods=['POST'])
def add_job():
    data = request.get_json(silent=True) or {}
    company = data.get('company', '').strip()
    position = data.get('position', '').strip()
    if not company or not position:
        return jsonify({'error': 'company and position are required'}), 400
    status = data.get('status', 'Applied')
    if status not in VALID_STATUSES:
        status = 'Applied'

    j = job_create({
        'company': company,
        'position': position,
        'status': status,
        'job_description': data.get('job_description', ''),
        'notes': data.get('notes', ''),
    })
    return jsonify(j), 201


@jobs_bp.route('/<job_id>', methods=['PUT'])
def update_job(job_id):
    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status'] not in VALID_STATUSES:
        data.pop('status')
    j = job_update(job_id, data)
    if j is None:
        abort(404)
    return jsonify(j)


@jobs_bp.route('/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    if not job_delete(job_id):
        abort(404)
    return jsonify({'success': True})


@jobs_bp.route('/analyze-jd', methods=['POST'])
def analyze_jd():
    data = request.get_json(silent=True) or {}
    job_description = data.get('job_description', '').strip()
    if not job_description:
        return jsonify({'error': 'job_description is required'}), 400
    try:
        analysis = get_job_analysis(job_description)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/stats', methods=['GET'])
def get_stats():
    from models.settings import Setting

    use_fake = Setting.get('use_fake_stats', '0') == '1'

    if use_fake:
        BASE_TOTAL = 250
        BASE_INTERVIEW = 190
        BASE_OFFER = 156
        BASE_RATE = 82.0

        reload_count = int(Setting.get('dashboard_reload_count', '0'))
        reload_count += 1
        Setting.set('dashboard_reload_count', str(reload_count))

        factor = 1.02 ** reload_count
        total = round(BASE_TOTAL * factor)
        interview = round(BASE_INTERVIEW * factor)
        offer = round(BASE_OFFER * factor)
        interview_rate = round(min(BASE_RATE * factor, 99.9), 1)

        return jsonify({
            'total': total,
            'applied': max(total - interview - offer, 0),
            'interview': interview,
            'offer': offer,
            'rejected': 0,
            'interview_rate': interview_rate,
            'offer_rate': round((offer / total * 100), 1) if total > 0 else 0,
        })

    total = job_count()
    by_status = job_count_by_status()
    applied = by_status.get('Applied', 0)
    interview = by_status.get('Interview', 0)
    offer = by_status.get('Offer', 0)
    rejected = by_status.get('Rejected', 0)
    interview_rate = round((interview / total * 100), 1) if total > 0 else 0
    offer_rate = round((offer / total * 100), 1) if total > 0 else 0

    return jsonify({
        'total': total,
        'applied': applied,
        'interview': interview,
        'offer': offer,
        'rejected': rejected,
        'interview_rate': interview_rate,
        'offer_rate': offer_rate,
    })

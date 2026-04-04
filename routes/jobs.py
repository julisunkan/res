from flask import Blueprint, request, jsonify
from extensions import db
from models.job import Job
from utils.analyzer import get_job_analysis

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/', methods=['GET'])
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])


@jobs_bp.route('/', methods=['POST'])
def add_job():
    data = request.get_json()
    company = data.get('company', '').strip()
    position = data.get('position', '').strip()
    if not company or not position:
        return jsonify({'error': 'company and position are required'}), 400

    job = Job(
        company=company,
        position=position,
        status=data.get('status', 'Applied'),
        job_description=data.get('job_description', ''),
        notes=data.get('notes', ''),
    )
    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict()), 201


@jobs_bp.route('/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    if 'company' in data:
        job.company = data['company']
    if 'position' in data:
        job.position = data['position']
    if 'status' in data:
        job.status = data['status']
    if 'job_description' in data:
        job.job_description = data['job_description']
    if 'notes' in data:
        job.notes = data['notes']
    db.session.commit()
    return jsonify(job.to_dict())


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return jsonify({'success': True})


@jobs_bp.route('/analyze-jd', methods=['POST'])
def analyze_jd():
    data = request.get_json()
    job_description = data.get('job_description', '')
    if not job_description:
        return jsonify({'error': 'job_description is required'}), 400
    try:
        analysis = get_job_analysis(job_description)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/stats', methods=['GET'])
def get_stats():
    total = Job.query.count()
    applied = Job.query.filter_by(status='Applied').count()
    interview = Job.query.filter_by(status='Interview').count()
    offer = Job.query.filter_by(status='Offer').count()
    rejected = Job.query.filter_by(status='Rejected').count()
    interview_rate = (interview / total * 100) if total > 0 else 0
    return jsonify({
        'total': total,
        'applied': applied,
        'interview': interview,
        'offer': offer,
        'rejected': rejected,
        'interview_rate': round(interview_rate, 1),
    })

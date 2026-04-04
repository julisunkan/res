import json
from flask import Blueprint, request, jsonify, send_file
from extensions import db
from models.resume import Resume
from utils.parser import extract_text
from utils.ai_engine import optimize_resume, generate_cover_letter, rewrite_section, generate_resume_from_skills
from utils.analyzer import get_match_analysis
from utils.pdf_exporter import generate_pdf

resume_bp = Blueprint('resume', __name__)


@resume_bp.route('/upload', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
    try:
        text = extract_text(file.read(), file.filename)
        return jsonify({'text': text, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@resume_bp.route('/analyze', methods=['POST'])
def analyze_resume():
    data = request.get_json()
    resume_text = data.get('resume_text', '')
    job_description = data.get('job_description', '')
    if not resume_text or not job_description:
        return jsonify({'error': 'resume_text and job_description are required'}), 400
    try:
        analysis = get_match_analysis(resume_text, job_description)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resume_bp.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    resume_text = data.get('resume_text', '')
    job_description = data.get('job_description', '')
    label = data.get('label', 'Optimized Resume')
    if not resume_text or not job_description:
        return jsonify({'error': 'resume_text and job_description are required'}), 400
    try:
        optimized = optimize_resume(resume_text, job_description)
        cover = generate_cover_letter(resume_text, job_description)
        analysis = get_match_analysis(resume_text, job_description)

        resume = Resume(
            label=label,
            original_text=resume_text,
            optimized_text=optimized,
            cover_letter=cover,
            match_score=analysis.get('score', 0),
            missing_keywords=json.dumps(analysis.get('missing_keywords', [])),
            suggestions=json.dumps(analysis.get('suggestions', [])),
        )
        db.session.add(resume)
        db.session.commit()

        return jsonify({
            'id': resume.id,
            'optimized_text': optimized,
            'cover_letter': cover,
            'match_score': analysis.get('score', 0),
            'missing_keywords': analysis.get('missing_keywords', []),
            'suggestions': analysis.get('suggestions', []),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resume_bp.route('/rewrite-section', methods=['POST'])
def rewrite_section_route():
    data = request.get_json()
    section_text = data.get('section_text', '')
    section_name = data.get('section_name', 'Section')
    job_description = data.get('job_description', '')
    if not section_text:
        return jsonify({'error': 'section_text is required'}), 400
    try:
        rewritten = rewrite_section(section_text, section_name, job_description)
        return jsonify({'rewritten': rewritten})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resume_bp.route('/generate-from-skills', methods=['POST'])
def generate_from_skills():
    data = request.get_json()
    name = data.get('name', '')
    skills = data.get('skills', '')
    education = data.get('education', '')
    experience_notes = data.get('experience_notes', '')
    if not name or not skills:
        return jsonify({'error': 'name and skills are required'}), 400
    try:
        resume_text = generate_resume_from_skills(name, skills, education, experience_notes)
        return jsonify({'resume_text': resume_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resume_bp.route('/list', methods=['GET'])
def list_resumes():
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    return jsonify([r.to_dict() for r in resumes])


@resume_bp.route('/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    return jsonify(resume.to_dict())


@resume_bp.route('/<int:resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    db.session.delete(resume)
    db.session.commit()
    return jsonify({'success': True})


@resume_bp.route('/export/<int:resume_id>/<doc_type>', methods=['GET'])
def export_resume(resume_id, doc_type):
    resume = Resume.query.get_or_404(resume_id)
    if doc_type == 'resume':
        content = resume.optimized_text or resume.original_text or ''
        title = f"Resume - {resume.label}"
        filename = f"resume_{resume.id}.pdf"
    elif doc_type == 'cover_letter':
        content = resume.cover_letter or ''
        title = f"Cover Letter - {resume.label}"
        filename = f"cover_letter_{resume.id}.pdf"
    else:
        return jsonify({'error': 'Invalid doc_type'}), 400

    try:
        pdf_buffer = generate_pdf(title, content)
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

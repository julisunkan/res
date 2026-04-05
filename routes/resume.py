import json
from flask import Blueprint, request, jsonify, send_file, abort
from utils.data_layer import (
    resume_list, resume_get, resume_create, resume_update, resume_delete,
)
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
    allowed = ('.pdf', '.docx')
    if not file.filename.lower().endswith(allowed):
        return jsonify({'error': 'Only PDF and DOCX files are supported'}), 400
    try:
        text = extract_text(file.read(), file.filename)
        if not text.strip():
            return jsonify({'error': 'Could not extract text from the file. The file may be image-based.'}), 400
        return jsonify({'text': text, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@resume_bp.route('/analyze', methods=['POST'])
def analyze_resume():
    data = request.get_json(silent=True) or {}
    resume_text = data.get('resume_text', '').strip()
    job_description = data.get('job_description', '').strip()
    if not resume_text or not job_description:
        return jsonify({'error': 'resume_text and job_description are required'}), 400
    try:
        analysis = get_match_analysis(resume_text, job_description)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@resume_bp.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json(silent=True) or {}
    resume_text = data.get('resume_text', '').strip()
    job_description = data.get('job_description', '').strip()
    label = data.get('label', 'Optimized Resume').strip() or 'Optimized Resume'
    if not resume_text or not job_description:
        return jsonify({'error': 'resume_text and job_description are required'}), 400
    try:
        optimized = optimize_resume(resume_text, job_description)
        cover = generate_cover_letter(resume_text, job_description)
        analysis = get_match_analysis(resume_text, job_description)

        resume = resume_create({
            'label': label,
            'original_text': resume_text,
            'optimized_text': optimized,
            'cover_letter': cover,
            'match_score': analysis.get('score', 0),
            'missing_keywords': json.dumps(analysis.get('missing_keywords', [])),
            'suggestions': json.dumps(analysis.get('suggestions', [])),
        })

        return jsonify({
            'id': resume['id'],
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
    data = request.get_json(silent=True) or {}
    section_text = data.get('section_text', '').strip()
    section_name = data.get('section_name', 'Section').strip() or 'Section'
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
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    skills = data.get('skills', '').strip()
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
    return jsonify(resume_list())


@resume_bp.route('/<resume_id>', methods=['GET'])
def get_resume(resume_id):
    r = resume_get(resume_id)
    if r is None:
        abort(404)
    return jsonify(r)


@resume_bp.route('/<resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    if not resume_delete(resume_id):
        abort(404)
    return jsonify({'success': True})


@resume_bp.route('/export/<resume_id>/<doc_type>', methods=['GET'])
def export_resume(resume_id, doc_type):
    r = resume_get(resume_id)
    if r is None:
        abort(404)
    if doc_type == 'resume':
        content = r.get('optimized_text') or r.get('original_text') or ''
        title = f"Resume - {r.get('label', '')}"
        filename = f"resume_{r['id']}.pdf"
    elif doc_type == 'cover_letter':
        content = r.get('cover_letter') or ''
        title = f"Cover Letter - {r.get('label', '')}"
        filename = f"cover_letter_{r['id']}.pdf"
    else:
        return jsonify({'error': 'Invalid doc_type. Use "resume" or "cover_letter"'}), 400

    if not content.strip():
        return jsonify({'error': 'No content available to export for this document'}), 400

    try:
        pdf_buffer = generate_pdf(title, content)
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

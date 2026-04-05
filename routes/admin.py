import json
import os
import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, Response
from extensions import db
from models.settings import Setting
from models.resume import Resume
from models.job import Job

admin_bp = Blueprint('admin', __name__)

ADMIN_PASSWORD_KEY = 'admin_password'
DEFAULT_PASSWORD = 'admin123'


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login_page'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('')
@admin_bp.route('/')
def login_page():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/login.html')


@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    password = data.get('password', '')
    stored = Setting.get(ADMIN_PASSWORD_KEY, DEFAULT_PASSWORD)
    if password == stored:
        session['admin_logged_in'] = True
        session.permanent = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Incorrect password'}), 401


@admin_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


# ── SETTINGS API ─────────────────────────────────────────────────────────────

@admin_bp.route('/api/settings', methods=['GET'])
@admin_required
def get_settings():
    sensitive = {'groq_api_key', ADMIN_PASSWORD_KEY}
    rows = Setting.query.order_by(Setting.key).all()
    result = {}
    for r in rows:
        if r.key in sensitive:
            result[r.key] = '••••••••' if r.value else ''
        else:
            result[r.key] = r.value or ''
    # Always include known keys even if unset
    defaults = {
        'groq_api_key': '',
        'app_name': 'AI Resume & Cover Letter Creator',
        'app_tagline': 'Your intelligent job application assistant — from resume to offer letter.',
        'max_upload_mb': '10',
        'ai_model': 'llama-3.3-70b-versatile',
        'ai_max_tokens': '4096',
        ADMIN_PASSWORD_KEY: '',
        'analytics_id': '',
        'adsense_publisher_id': '',
        'ad_top_banner_enabled': '0',
        'ad_top_banner_slot': '',
        'ad_results_enabled': '0',
        'ad_results_slot': '',
        'ad_sidebar_enabled': '0',
        'ad_sidebar_slot': '',
    }
    for k, v in defaults.items():
        if k not in result:
            result[k] = v
    return jsonify(result)


@admin_bp.route('/api/settings', methods=['POST'])
@admin_required
def save_settings():
    data = request.get_json()
    skip_mask = {'••••••••'}
    for key, value in data.items():
        if value in skip_mask:
            continue
        if value is not None:
            Setting.set(key, str(value))
    return jsonify({'success': True})


@admin_bp.route('/api/settings/test-groq', methods=['POST'])
@admin_required
def test_groq():
    api_key = Setting.get('groq_api_key', '')
    if not api_key:
        return jsonify({'success': False, 'error': 'No API key saved'})
    try:
        from groq import Groq
        from utils.ai_engine import _get_model
        client = Groq(api_key=api_key)
        model = _get_model()
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': 'Say "OK" in one word.'}],
            max_tokens=5,
        )
        return jsonify({'success': True, 'response': resp.choices[0].message.content.strip(), 'model': model})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ── RESUMES API ───────────────────────────────────────────────────────────────

@admin_bp.route('/api/resumes', methods=['GET'])
@admin_required
def list_resumes():
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    return jsonify([r.to_dict() for r in resumes])


@admin_bp.route('/api/resumes/<int:rid>', methods=['GET'])
@admin_required
def get_resume(rid):
    r = Resume.query.get_or_404(rid)
    return jsonify(r.to_dict())


@admin_bp.route('/api/resumes/<int:rid>', methods=['PUT'])
@admin_required
def update_resume(rid):
    r = Resume.query.get_or_404(rid)
    data = request.get_json()
    for field in ('label', 'original_text', 'optimized_text', 'cover_letter', 'match_score', 'missing_keywords', 'suggestions'):
        if field in data:
            setattr(r, field, data[field])
    db.session.commit()
    return jsonify(r.to_dict())


@admin_bp.route('/api/resumes/<int:rid>', methods=['DELETE'])
@admin_required
def delete_resume(rid):
    r = Resume.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/resumes/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_resumes():
    data = request.get_json()
    ids = data.get('ids', [])
    Resume.query.filter(Resume.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True, 'deleted': len(ids)})


# ── JOBS API ──────────────────────────────────────────────────────────────────

@admin_bp.route('/api/jobs', methods=['GET'])
@admin_required
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])


@admin_bp.route('/api/jobs/<int:jid>', methods=['PUT'])
@admin_required
def update_job(jid):
    j = Job.query.get_or_404(jid)
    data = request.get_json()
    for field in ('company', 'position', 'status', 'notes', 'job_description'):
        if field in data:
            setattr(j, field, data[field])
    db.session.commit()
    return jsonify(j.to_dict())


@admin_bp.route('/api/jobs/<int:jid>', methods=['DELETE'])
@admin_required
def delete_job(jid):
    j = Job.query.get_or_404(jid)
    db.session.delete(j)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/jobs/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_jobs():
    data = request.get_json()
    ids = data.get('ids', [])
    Job.query.filter(Job.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True, 'deleted': len(ids)})


# ── ADS.TXT ───────────────────────────────────────────────────────────────────

@admin_bp.route('/api/ads-txt', methods=['GET'])
@admin_required
def get_ads_txt():
    content = Setting.get('ads_txt_content', '')
    return jsonify({'content': content})


@admin_bp.route('/api/ads-txt', methods=['POST'])
@admin_required
def save_ads_txt():
    if request.content_type and 'multipart/form-data' in request.content_type:
        f = request.files.get('file')
        if not f or not f.filename:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        content = f.read().decode('utf-8', errors='replace')
    else:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
    Setting.set('ads_txt_content', content)
    return jsonify({'success': True})


# ── STATS ─────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/stats', methods=['GET'])
@admin_required
def get_stats():
    return jsonify({
        'resumes': Resume.query.count(),
        'jobs': Job.query.count(),
        'interviews': Job.query.filter_by(status='Interview').count(),
        'offers': Job.query.filter_by(status='Offer').count(),
    })


# ── DATABASE CONFIG ───────────────────────────────────────────────────────────

@admin_bp.route('/api/database/config', methods=['GET'])
@admin_required
def get_db_config():
    from utils.db_manager import load_config
    cfg = load_config()
    safe = dict(cfg)
    if safe.get('mysql_password'):
        safe['mysql_password'] = '••••••••'
    return jsonify(safe)


@admin_bp.route('/api/database/config', methods=['POST'])
@admin_required
def save_db_config():
    from utils.db_manager import load_config, save_config
    data = request.get_json()
    cfg = load_config()
    cfg['db_type'] = data.get('db_type', 'sqlite')
    cfg['mysql_host'] = data.get('mysql_host', 'localhost')
    cfg['mysql_port'] = int(data.get('mysql_port', 3306))
    cfg['mysql_database'] = data.get('mysql_database', '')
    cfg['mysql_user'] = data.get('mysql_user', '')
    if data.get('mysql_password') and data['mysql_password'] != '••••••••':
        cfg['mysql_password'] = data['mysql_password']
    save_config(cfg)
    return jsonify({'success': True})


@admin_bp.route('/api/database/test-mysql', methods=['POST'])
@admin_required
def test_mysql():
    from utils.db_manager import load_config, test_mysql_connection
    data = request.get_json()
    cfg = load_config()
    host = data.get('mysql_host', cfg.get('mysql_host', 'localhost'))
    port = data.get('mysql_port', cfg.get('mysql_port', 3306))
    database = data.get('mysql_database', cfg.get('mysql_database', ''))
    user = data.get('mysql_user', cfg.get('mysql_user', ''))
    password = data.get('mysql_password', '')
    if password == '••••••••':
        password = cfg.get('mysql_password', '')
    ok, err = test_mysql_connection(host, port, database, user, password)
    if ok:
        return jsonify({'success': True, 'message': 'Connected successfully!'})
    return jsonify({'success': False, 'error': err})


# ── DATABASE EXPORT ───────────────────────────────────────────────────────────

@admin_bp.route('/api/database/export/sqlite', methods=['GET'])
@admin_required
def export_sqlite():
    from utils.db_manager import export_as_sqlite
    try:
        data = export_as_sqlite()
        ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return Response(
            data,
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename=resume_app_{ts}.sqlite.sql'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/database/export/mysql', methods=['GET'])
@admin_required
def export_mysql():
    from utils.db_manager import export_as_mysql
    try:
        data = export_as_mysql()
        ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return Response(
            data,
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename=resume_app_{ts}.mysql.sql'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/database/restart', methods=['POST'])
@admin_required
def restart_app():
    import threading
    def _restart():
        import time
        import signal
        time.sleep(0.8)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_restart, daemon=True).start()
    return jsonify({'success': True})

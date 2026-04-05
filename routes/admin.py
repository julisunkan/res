import json
import os
import datetime
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, Response, abort
from extensions import db
from models.settings import Setting
from models.resume import Resume
from models.job import Job
from models.contact_message import ContactMessage

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
    data = request.get_json(silent=True) or {}
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
        # AI
        'groq_api_key': '',
        'ai_model': 'llama-3.3-70b-versatile',
        'ai_max_tokens': '4096',
        # Branding
        'app_name': 'AI Resume & Cover Letter Creator',
        'app_tagline': 'Your intelligent job application assistant — from resume to offer letter.',
        # Website identity
        'site_url': '',
        'contact_email': '',
        'meta_description': 'AI-powered resume builder, cover letter generator, and career assistant.',
        'meta_keywords': 'resume builder, cover letter, AI, job application, career',
        # Social media
        'twitter_url': '',
        'linkedin_url': '',
        'facebook_url': '',
        'instagram_url': '',
        'youtube_url': '',
        # SEO & verification
        'google_search_console': '',
        # Performance
        'max_upload_mb': '10',
        'use_fake_stats': '0',
        # Security
        ADMIN_PASSWORD_KEY: '',
        # Analytics & monetization
        'analytics_id': '',
        'adsense_publisher_id': '',
        'adsense_auto_ads': '0',
        'ad_top_banner_enabled': '0',
        'ad_top_banner_slot': '',
        'ad_results_enabled': '0',
        'ad_results_slot': '',
        'ad_sidebar_enabled': '0',
        'ad_sidebar_slot': '',
        # Job board APIs
        'adzuna_app_id': '',
        'adzuna_app_key': '',
        # Appearance
        'hide_footer': '0',
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
    from utils.data_layer import resume_list
    return jsonify(resume_list())


@admin_bp.route('/api/resumes/<rid>', methods=['GET'])
@admin_required
def get_resume(rid):
    from utils.data_layer import resume_get
    r = resume_get(rid)
    if r is None:
        abort(404)
    return jsonify(r)


@admin_bp.route('/api/resumes/<rid>', methods=['PUT'])
@admin_required
def update_resume(rid):
    from utils.data_layer import resume_update
    data = request.get_json(silent=True) or {}
    r = resume_update(rid, data)
    if r is None:
        abort(404)
    return jsonify(r)


@admin_bp.route('/api/resumes/<rid>', methods=['DELETE'])
@admin_required
def delete_resume(rid):
    from utils.data_layer import resume_delete
    if not resume_delete(rid):
        abort(404)
    return jsonify({'success': True})


@admin_bp.route('/api/resumes/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_resumes():
    from utils.data_layer import resume_bulk_delete
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    deleted = resume_bulk_delete(ids)
    return jsonify({'success': True, 'deleted': deleted})


# ── JOBS API ──────────────────────────────────────────────────────────────────

@admin_bp.route('/api/jobs', methods=['GET'])
@admin_required
def list_jobs():
    from utils.data_layer import job_list
    return jsonify(job_list())


@admin_bp.route('/api/jobs/<jid>', methods=['PUT'])
@admin_required
def update_job(jid):
    from utils.data_layer import job_update
    data = request.get_json(silent=True) or {}
    j = job_update(jid, data)
    if j is None:
        abort(404)
    return jsonify(j)


@admin_bp.route('/api/jobs/<jid>', methods=['DELETE'])
@admin_required
def delete_job(jid):
    from utils.data_layer import job_delete
    if not job_delete(jid):
        abort(404)
    return jsonify({'success': True})


@admin_bp.route('/api/jobs/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_jobs():
    from utils.data_layer import job_bulk_delete
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    deleted = job_bulk_delete(ids)
    return jsonify({'success': True, 'deleted': deleted})


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
    from utils.data_layer import (
        resume_count, job_count, job_count_by_status,
        message_count, message_count_unread,
    )
    by_status = job_count_by_status()
    return jsonify({
        'resumes': resume_count(),
        'jobs': job_count(),
        'interviews': by_status.get('Interview', 0),
        'offers': by_status.get('Offer', 0),
        'messages': message_count(),
        'unread_messages': message_count_unread(),
    })


# ── CONTACT MESSAGES API ──────────────────────────────────────────────────────

@admin_bp.route('/api/messages', methods=['GET'])
@admin_required
def list_messages():
    from utils.data_layer import message_list
    return jsonify(message_list())


@admin_bp.route('/api/messages/<mid>', methods=['GET'])
@admin_required
def get_message(mid):
    from utils.data_layer import message_get, message_set_read
    m = message_get(mid)
    if m is None:
        abort(404)
    if not m.get('is_read'):
        message_set_read(mid, True)
        m['is_read'] = True
    return jsonify(m)


@admin_bp.route('/api/messages/<mid>/read', methods=['POST'])
@admin_required
def mark_read(mid):
    from utils.data_layer import message_set_read
    if not message_set_read(mid, True):
        abort(404)
    return jsonify({'success': True})


@admin_bp.route('/api/messages/<mid>/unread', methods=['POST'])
@admin_required
def mark_unread(mid):
    from utils.data_layer import message_set_read
    if not message_set_read(mid, False):
        abort(404)
    return jsonify({'success': True})


@admin_bp.route('/api/messages/<mid>', methods=['DELETE'])
@admin_required
def delete_message(mid):
    from utils.data_layer import message_delete
    if not message_delete(mid):
        abort(404)
    return jsonify({'success': True})


@admin_bp.route('/api/messages/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_messages():
    from utils.data_layer import message_bulk_delete
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    deleted = message_bulk_delete(ids)
    return jsonify({'success': True, 'deleted': deleted})


# ── DATABASE CONFIG ───────────────────────────────────────────────────────────

@admin_bp.route('/api/database/config', methods=['GET'])
@admin_required
def get_db_config():
    from utils.db_manager import load_config
    from extensions import db
    cfg = load_config()
    safe = dict(cfg)
    if safe.get('mysql_password'):
        safe['mysql_password'] = '••••••••'
    # Report the actual URI the app is using (may differ from config if fallback occurred)
    actual_uri = str(db.engine.url)
    if 'mysql' in actual_uri:
        safe['active_db'] = 'mysql'
    else:
        safe['active_db'] = 'sqlite'
        if cfg.get('db_type') == 'mysql':
            safe['fallback_warning'] = True
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
    # Mirror db connection config into Settings table so it's exportable
    try:
        Setting.set('db_type', cfg['db_type'])
        Setting.set('mysql_host', cfg.get('mysql_host', ''))
        Setting.set('mysql_port', str(cfg.get('mysql_port', 3306)))
        Setting.set('mysql_database', cfg.get('mysql_database', ''))
        Setting.set('mysql_user', cfg.get('mysql_user', ''))
        if cfg.get('mysql_password'):
            Setting.set('mysql_password', cfg['mysql_password'])
    except Exception:
        pass
    return jsonify({'success': True})


# ── SETTINGS JSON EXPORT / IMPORT ─────────────────────────────────────────────

@admin_bp.route('/api/settings/export-json', methods=['GET'])
@admin_required
def export_settings_json():
    import json as _json
    sensitive = {'admin_password', 'groq_api_key', 'mysql_password'}
    rows = Setting.query.order_by(Setting.key).all()
    data = {}
    for r in rows:
        data[r.key] = '[REDACTED]' if r.key in sensitive else (r.value or '')
    ts = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return Response(
        _json.dumps(data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=settings_{ts}.json'}
    )


@admin_bp.route('/api/settings/import-json', methods=['POST'])
@admin_required
def import_settings_json():
    import json as _json
    sensitive = {'admin_password', 'groq_api_key', 'mysql_password'}
    f = request.files.get('file')
    if not f:
        raw = request.get_json(silent=True) or {}
        data = raw
    else:
        try:
            data = _json.loads(f.read().decode('utf-8'))
        except Exception as e:
            return jsonify({'success': False, 'error': f'Invalid JSON: {e}'}), 400
    count = 0
    skipped = []
    for key, value in data.items():
        if value == '[REDACTED]':
            skipped.append(key)
            continue
        if key in sensitive:
            skipped.append(key)
            continue
        Setting.set(str(key), str(value))
        count += 1
    msg = f'Imported {count} settings.'
    if skipped:
        msg += f' Skipped {len(skipped)} sensitive/redacted keys: {", ".join(skipped)}'
    return jsonify({'success': True, 'message': msg, 'imported': count, 'skipped': skipped})


@admin_bp.route('/api/database/import-sql', methods=['POST'])
@admin_required
def import_sql():
    from utils.db_manager import load_config, import_sql_dump
    f = request.files.get('file')
    if not f:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    try:
        sql_text = f.read().decode('utf-8', errors='replace')
        cfg = load_config()
        result = import_sql_dump(sql_text, cfg)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    use_ssl = bool(data.get('use_ssl', False))
    ok, msg = test_mysql_connection(host, port, database, user, password, use_ssl=use_ssl)
    if ok:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg})


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


# ── FIREBASE / FIRESTORE ───────────────────────────────────────────────────────

@admin_bp.route('/api/firebase/status', methods=['GET'])
@admin_required
def firebase_status():
    creds = Setting.get('firebase_service_account', '') or ''
    has_creds = bool(creds)
    project_id = ''
    client_email = ''
    if has_creds:
        try:
            data = json.loads(creds)
            project_id = data.get('project_id', '')
            client_email = data.get('client_email', '')
        except Exception:
            pass
    return jsonify({
        'configured': has_creds,
        'project_id': project_id,
        'client_email': client_email,
    })


@admin_bp.route('/api/firebase/save-credentials', methods=['POST'])
@admin_required
def firebase_save_credentials():
    data = request.get_json(silent=True) or {}
    creds_json = data.get('credentials', '').strip()
    if not creds_json:
        return jsonify({'success': False, 'error': 'No credentials provided.'})
    try:
        parsed = json.loads(creds_json)
        if parsed.get('type') != 'service_account':
            return jsonify({'success': False, 'error': 'Invalid service account JSON — "type" must be "service_account".'})
        from utils.firestore_manager import reset_firebase_app
        reset_firebase_app()
        Setting.set('firebase_service_account', creds_json)
        return jsonify({'success': True, 'project_id': parsed.get('project_id', '')})
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Invalid JSON: {e}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/api/firebase/clear-credentials', methods=['POST'])
@admin_required
def firebase_clear_credentials():
    try:
        from utils.firestore_manager import reset_firebase_app
        reset_firebase_app()
        Setting.set('firebase_service_account', '')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/api/firebase/test', methods=['POST'])
@admin_required
def firebase_test():
    try:
        from utils.firestore_manager import test_connection
        ok, msg = test_connection()
        return jsonify({'success': ok, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/api/firebase/export', methods=['POST'])
@admin_required
def firebase_export():
    data = request.get_json(silent=True) or {}
    collections = data.get('collections', ['resumes', 'jobs'])
    try:
        from utils.firestore_manager import export_collection
        results = {}

        if 'resumes' in collections:
            rows = [r.to_dict() for r in Resume.query.all()]
            results['resumes'] = export_collection('resumes', rows)

        if 'jobs' in collections:
            rows = [j.to_dict() for j in Job.query.all()]
            results['jobs'] = export_collection('jobs', rows)

        if 'settings' in collections:
            sensitive = {'admin_password', 'groq_api_key', 'mysql_password', 'firebase_service_account'}
            rows = [
                {'id': s.id, 'key': s.key, 'value': s.value}
                for s in Setting.query.all()
                if s.key not in sensitive
            ]
            results['settings'] = export_collection('settings', rows)

        if 'messages' in collections:
            rows = [m.to_dict() for m in ContactMessage.query.all()]
            results['contact_messages'] = export_collection('contact_messages', rows)

        return jsonify({'success': True, 'results': results, 'total': sum(results.values())})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@admin_bp.route('/api/firebase/import', methods=['POST'])
@admin_required
def firebase_import():
    data = request.get_json(silent=True) or {}
    collections = data.get('collections', ['resumes', 'jobs'])
    try:
        from utils.firestore_manager import import_collection
        results = {}

        if 'resumes' in collections:
            rows = import_collection('resumes')
            added = 0
            for row in rows:
                rid = row.get('id')
                if rid and not db.session.get(Resume, int(rid)):
                    r = Resume(
                        id=int(rid),
                        label=row.get('label') or 'Imported Resume',
                        original_text=row.get('original_text') or '',
                        optimized_text=row.get('optimized_text') or '',
                        cover_letter=row.get('cover_letter') or '',
                        match_score=float(row.get('match_score') or 0),
                        missing_keywords=row.get('missing_keywords') or '[]',
                        suggestions=row.get('suggestions') or '[]',
                    )
                    db.session.add(r)
                    added += 1
            db.session.commit()
            results['resumes'] = added

        if 'jobs' in collections:
            rows = import_collection('jobs')
            added = 0
            for row in rows:
                jid = row.get('id')
                if jid and not db.session.get(Job, int(jid)):
                    j = Job(
                        id=int(jid),
                        company=row.get('company') or '',
                        position=row.get('position') or '',
                        status=row.get('status') or 'Applied',
                        job_description=row.get('job_description') or '',
                        notes=row.get('notes') or '',
                    )
                    db.session.add(j)
                    added += 1
            db.session.commit()
            results['jobs'] = added

        return jsonify({'success': True, 'results': results, 'total': sum(results.values())})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

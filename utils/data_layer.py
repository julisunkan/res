"""
data_layer.py — Unified storage backend for Resumes, Jobs, and ContactMessages.

When db_type == 'firebase', all reads/writes go to Firestore.
Settings always stay in the local SQL database (they hold connection config).
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_RESUME_FIELDS = {
    'label', 'original_text', 'optimized_text', 'cover_letter',
    'match_score', 'missing_keywords', 'suggestions',
}
_JOB_FIELDS = {
    'company', 'position', 'status', 'job_description', 'notes', 'applied_date',
}
_MSG_FIELDS = {'name', 'email', 'subject', 'message', 'is_read'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def use_firebase():
    from models.settings import Setting
    return Setting.get('db_type', 'sqlite') == 'firebase'


def _now():
    return datetime.utcnow().isoformat()


def _next_id(collection_name):
    """Atomically increment and return the next integer ID for a collection."""
    from utils.firestore_manager import get_firestore_client
    from google.cloud import firestore as _gfs

    db = get_firestore_client()
    counter_ref = db.collection('_counters').document(collection_name)

    @_gfs.transactional
    def _txn(transaction, ref):
        snap = ref.get(transaction=transaction)
        current = int(snap.get('value')) if snap.exists else 0
        nv = current + 1
        transaction.set(ref, {'value': nv})
        return nv

    return _txn(db.transaction(), counter_ref)


def _fs_col(collection_name):
    from utils.firestore_manager import get_firestore_client
    return get_firestore_client().collection(collection_name)


def _doc_to_dict(doc):
    d = doc.to_dict()
    if d is None:
        return None
    d['id'] = int(doc.id) if str(doc.id).isdigit() else doc.id
    return d


# ── RESUME ────────────────────────────────────────────────────────────────────

def resume_list():
    if use_firebase():
        docs = _fs_col('resumes').stream()
        rows = [_doc_to_dict(d) for d in docs if d.to_dict()]
        rows.sort(key=lambda r: r.get('created_at') or '', reverse=True)
        return rows
    from models.resume import Resume
    return [r.to_dict() for r in Resume.query.order_by(Resume.created_at.desc()).all()]


def resume_get(resume_id):
    if use_firebase():
        doc = _fs_col('resumes').document(str(resume_id)).get()
        if not doc.exists:
            return None
        return _doc_to_dict(doc)
    from extensions import db
    from models.resume import Resume
    r = db.session.get(Resume, int(resume_id))
    return r.to_dict() if r else None


def resume_create(data):
    if use_firebase():
        new_id = _next_id('resumes')
        now = _now()
        doc = {
            'id': new_id,
            'label': data.get('label') or 'My Resume',
            'original_text': data.get('original_text') or '',
            'optimized_text': data.get('optimized_text') or '',
            'cover_letter': data.get('cover_letter') or '',
            'match_score': float(data.get('match_score') or 0),
            'missing_keywords': data.get('missing_keywords') or '[]',
            'suggestions': data.get('suggestions') or '[]',
            'created_at': now,
            'updated_at': now,
        }
        _fs_col('resumes').document(str(new_id)).set(doc)
        return dict(doc)

    from extensions import db
    from models.resume import Resume
    r = Resume(
        label=data.get('label') or 'My Resume',
        original_text=data.get('original_text') or '',
        optimized_text=data.get('optimized_text') or '',
        cover_letter=data.get('cover_letter') or '',
        match_score=float(data.get('match_score') or 0),
        missing_keywords=data.get('missing_keywords') or '[]',
        suggestions=data.get('suggestions') or '[]',
    )
    db.session.add(r)
    db.session.commit()
    return r.to_dict()


def resume_update(resume_id, data):
    if use_firebase():
        ref = _fs_col('resumes').document(str(resume_id))
        doc = ref.get()
        if not doc.exists:
            return None
        updates = {k: v for k, v in data.items() if k in _RESUME_FIELDS}
        updates['updated_at'] = _now()
        ref.update(updates)
        return _doc_to_dict(ref.get())

    from extensions import db
    from models.resume import Resume
    r = db.session.get(Resume, int(resume_id))
    if not r:
        return None
    for k, v in data.items():
        if hasattr(r, k) and k not in ('id',):
            setattr(r, k, v)
    db.session.commit()
    return r.to_dict()


def resume_delete(resume_id):
    if use_firebase():
        ref = _fs_col('resumes').document(str(resume_id))
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    from extensions import db
    from models.resume import Resume
    r = db.session.get(Resume, int(resume_id))
    if not r:
        return False
    db.session.delete(r)
    db.session.commit()
    return True


def resume_bulk_delete(ids):
    if use_firebase():
        col = _fs_col('resumes')
        batch = get_firestore_client().batch()
        count = 0
        for rid in ids:
            batch.delete(col.document(str(rid)))
            count += 1
        batch.commit()
        return count

    from extensions import db
    from models.resume import Resume
    deleted = Resume.query.filter(Resume.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return deleted


def resume_count():
    if use_firebase():
        return len(list(_fs_col('resumes').stream()))
    from models.resume import Resume
    return Resume.query.count()


# ── JOB ───────────────────────────────────────────────────────────────────────

def job_list():
    if use_firebase():
        docs = _fs_col('jobs').stream()
        rows = [_doc_to_dict(d) for d in docs if d.to_dict()]
        rows.sort(key=lambda r: r.get('created_at') or '', reverse=True)
        return rows
    from models.job import Job
    return [j.to_dict() for j in Job.query.order_by(Job.created_at.desc()).all()]


def job_get(job_id):
    if use_firebase():
        doc = _fs_col('jobs').document(str(job_id)).get()
        if not doc.exists:
            return None
        return _doc_to_dict(doc)
    from extensions import db
    from models.job import Job
    j = db.session.get(Job, int(job_id))
    return j.to_dict() if j else None


def job_create(data):
    if use_firebase():
        new_id = _next_id('jobs')
        now = _now()
        doc = {
            'id': new_id,
            'company': data.get('company') or '',
            'position': data.get('position') or '',
            'status': data.get('status') or 'Applied',
            'job_description': data.get('job_description') or '',
            'notes': data.get('notes') or '',
            'applied_date': now,
            'created_at': now,
            'updated_at': now,
        }
        _fs_col('jobs').document(str(new_id)).set(doc)
        return dict(doc)

    from extensions import db
    from models.job import Job
    j = Job(
        company=data.get('company') or '',
        position=data.get('position') or '',
        status=data.get('status') or 'Applied',
        job_description=data.get('job_description') or '',
        notes=data.get('notes') or '',
    )
    db.session.add(j)
    db.session.commit()
    return j.to_dict()


def job_update(job_id, data):
    if use_firebase():
        ref = _fs_col('jobs').document(str(job_id))
        doc = ref.get()
        if not doc.exists:
            return None
        updates = {k: v for k, v in data.items() if k in _JOB_FIELDS}
        updates['updated_at'] = _now()
        ref.update(updates)
        return _doc_to_dict(ref.get())

    from extensions import db
    from models.job import Job
    j = db.session.get(Job, int(job_id))
    if not j:
        return None
    for k, v in data.items():
        if hasattr(j, k) and k not in ('id',):
            setattr(j, k, v)
    db.session.commit()
    return j.to_dict()


def job_delete(job_id):
    if use_firebase():
        ref = _fs_col('jobs').document(str(job_id))
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    from extensions import db
    from models.job import Job
    j = db.session.get(Job, int(job_id))
    if not j:
        return False
    db.session.delete(j)
    db.session.commit()
    return True


def job_bulk_delete(ids):
    if use_firebase():
        from utils.firestore_manager import get_firestore_client
        col = _fs_col('jobs')
        batch = get_firestore_client().batch()
        for jid in ids:
            batch.delete(col.document(str(jid)))
        batch.commit()
        return len(ids)

    from extensions import db
    from models.job import Job
    deleted = Job.query.filter(Job.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return deleted


def job_count():
    if use_firebase():
        return len(list(_fs_col('jobs').stream()))
    from models.job import Job
    return Job.query.count()


def job_count_by_status():
    if use_firebase():
        rows = [_doc_to_dict(d) for d in _fs_col('jobs').stream() if d.to_dict()]
        counts = {'Applied': 0, 'Interview': 0, 'Offer': 0, 'Rejected': 0}
        for r in rows:
            s = r.get('status', 'Applied')
            if s in counts:
                counts[s] += 1
        return counts

    from models.job import Job
    return {
        'Applied': Job.query.filter_by(status='Applied').count(),
        'Interview': Job.query.filter_by(status='Interview').count(),
        'Offer': Job.query.filter_by(status='Offer').count(),
        'Rejected': Job.query.filter_by(status='Rejected').count(),
    }


# ── CONTACT MESSAGE ────────────────────────────────────────────────────────────

def message_list():
    if use_firebase():
        docs = _fs_col('contact_messages').stream()
        rows = [_doc_to_dict(d) for d in docs if d.to_dict()]
        rows.sort(key=lambda r: r.get('created_at') or '', reverse=True)
        return rows
    from models.contact_message import ContactMessage
    return [m.to_dict() for m in ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()]


def message_get(msg_id):
    if use_firebase():
        doc = _fs_col('contact_messages').document(str(msg_id)).get()
        if not doc.exists:
            return None
        return _doc_to_dict(doc)
    from extensions import db
    from models.contact_message import ContactMessage
    m = db.session.get(ContactMessage, int(msg_id))
    return m.to_dict() if m else None


def message_create(data):
    if use_firebase():
        new_id = _next_id('contact_messages')
        now = _now()
        doc = {
            'id': new_id,
            'name': data.get('name') or '',
            'email': data.get('email') or '',
            'subject': data.get('subject') or '',
            'message': data.get('message') or '',
            'is_read': False,
            'created_at': now,
        }
        _fs_col('contact_messages').document(str(new_id)).set(doc)
        return dict(doc)

    from extensions import db
    from models.contact_message import ContactMessage
    m = ContactMessage(
        name=data.get('name') or '',
        email=data.get('email') or '',
        subject=data.get('subject') or '',
        message=data.get('message') or '',
    )
    db.session.add(m)
    db.session.commit()
    return m.to_dict()


def message_set_read(msg_id, is_read):
    if use_firebase():
        ref = _fs_col('contact_messages').document(str(msg_id))
        if not ref.get().exists:
            return False
        ref.update({'is_read': bool(is_read)})
        return True

    from extensions import db
    from models.contact_message import ContactMessage
    m = db.session.get(ContactMessage, int(msg_id))
    if not m:
        return False
    m.is_read = bool(is_read)
    db.session.commit()
    return True


def message_delete(msg_id):
    if use_firebase():
        ref = _fs_col('contact_messages').document(str(msg_id))
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    from extensions import db
    from models.contact_message import ContactMessage
    m = db.session.get(ContactMessage, int(msg_id))
    if not m:
        return False
    db.session.delete(m)
    db.session.commit()
    return True


def message_bulk_delete(ids):
    if use_firebase():
        from utils.firestore_manager import get_firestore_client
        col = _fs_col('contact_messages')
        batch = get_firestore_client().batch()
        for mid in ids:
            batch.delete(col.document(str(mid)))
        batch.commit()
        return len(ids)

    from extensions import db
    from models.contact_message import ContactMessage
    deleted = ContactMessage.query.filter(ContactMessage.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return deleted


def message_count():
    if use_firebase():
        return len(list(_fs_col('contact_messages').stream()))
    from models.contact_message import ContactMessage
    return ContactMessage.query.count()


def message_count_unread():
    if use_firebase():
        docs = _fs_col('contact_messages').stream()
        return sum(1 for d in docs if not (d.to_dict() or {}).get('is_read', False))
    from models.contact_message import ContactMessage
    return ContactMessage.query.filter_by(is_read=False).count()


# ── UTILS ─────────────────────────────────────────────────────────────────────

def get_firestore_client():
    from utils.firestore_manager import get_firestore_client as _gfc
    return _gfc()

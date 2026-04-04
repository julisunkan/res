import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from models.job_post import JobPost
from models.settings import Setting

logger = logging.getLogger(__name__)
job_board_bp = Blueprint('job_board', __name__, url_prefix='/api/jobboard')


def _get_groq_client():
    import groq
    key = Setting.get('groq_api_key', '')
    if not key:
        raise ValueError('Groq API key not configured.')
    return groq.Groq(api_key=key)


# ── Public API ──────────────────────────────────────────────────────────────

@job_board_bp.get('/published')
def public_list():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    search = request.args.get('q', '').strip().lower()
    job_type = request.args.get('type', '').strip().lower()
    tag = request.args.get('tag', '').strip().lower()

    q = JobPost.query.filter_by(status='published').order_by(JobPost.featured.desc(), JobPost.updated_at.desc())
    posts = q.all()

    if search:
        posts = [p for p in posts if search in (p.title or '').lower()
                 or search in (p.company or '').lower()
                 or search in (p.location or '').lower()]
    if job_type:
        posts = [p for p in posts if job_type in (p.job_type or '').lower()]
    if tag:
        posts = [p for p in posts if tag in (p.tags or '').lower()]

    total = len(posts)
    start = (page - 1) * per_page
    page_posts = posts[start:start + per_page]
    return jsonify({
        'total': total,
        'page': page,
        'pages': max(1, -(-total // per_page)),
        'posts': [p.to_dict() for p in page_posts],
    })


@job_board_bp.get('/published/<int:post_id>')
def public_detail(post_id):
    post = JobPost.query.filter_by(id=post_id, status='published').first_or_404()
    return jsonify(post.to_dict())


@job_board_bp.get('/featured')
def featured_posts():
    posts = JobPost.query.filter_by(status='published', featured=True).order_by(JobPost.updated_at.desc()).limit(6).all()
    if not posts:
        posts = JobPost.query.filter_by(status='published').order_by(JobPost.updated_at.desc()).limit(6).all()
    return jsonify([p.to_dict() for p in posts])


# ── Admin API ───────────────────────────────────────────────────────────────

@job_board_bp.get('/admin/posts')
def admin_list():
    status = request.args.get('status', 'all')
    q = JobPost.query.order_by(JobPost.created_at.desc())
    if status != 'all':
        q = q.filter_by(status=status)
    posts = q.all()

    counts = {
        'draft': JobPost.query.filter_by(status='draft').count(),
        'published': JobPost.query.filter_by(status='published').count(),
        'archived': JobPost.query.filter_by(status='archived').count(),
        'total': JobPost.query.count(),
    }
    return jsonify({'posts': [p.to_dict() for p in posts], 'counts': counts})


@job_board_bp.get('/admin/posts/<int:post_id>')
def admin_get(post_id):
    post = JobPost.query.get_or_404(post_id)
    d = post.to_dict()
    d['original_description'] = post.original_description
    d['description_raw'] = post.description
    return jsonify(d)


@job_board_bp.put('/admin/posts/<int:post_id>')
def admin_update(post_id):
    post = JobPost.query.get_or_404(post_id)
    data = request.json or {}
    for field in ['title', 'company', 'location', 'job_type', 'salary', 'apply_url', 'description']:
        if field in data:
            setattr(post, field, data[field])
    if 'tags' in data:
        tags = data['tags']
        post.tags = ', '.join(tags) if isinstance(tags, list) else tags
    if 'featured' in data:
        post.featured = bool(data['featured'])
    if 'status' in data and data['status'] in ('draft', 'published', 'archived'):
        post.status = data['status']
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'post': post.to_dict()})


@job_board_bp.delete('/admin/posts/<int:post_id>')
def admin_delete(post_id):
    post = JobPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True})


@job_board_bp.post('/admin/posts/bulk')
def admin_bulk():
    data = request.json or {}
    action = data.get('action')
    ids = data.get('ids', [])
    if not ids or action not in ('publish', 'archive', 'draft', 'delete'):
        return jsonify({'success': False, 'error': 'Invalid request'}), 400
    posts = JobPost.query.filter(JobPost.id.in_(ids)).all()
    if action == 'delete':
        for p in posts:
            db.session.delete(p)
    else:
        for p in posts:
            p.status = action
            p.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'affected': len(posts)})


@job_board_bp.post('/admin/posts/<int:post_id>/rewrite')
def admin_rewrite(post_id):
    post = JobPost.query.get_or_404(post_id)
    source_text = post.original_description or post.description
    if not source_text or len(source_text.strip()) < 50:
        return jsonify({'success': False, 'error': 'Job description is too short to rewrite.'}), 400

    try:
        client = _get_groq_client()
        model = Setting.get('ai_model', 'llama-3.3-70b-versatile')
        prompt = f"""You are a professional job description writer. Rewrite the following job posting completely in your own words. 

Rules:
- Preserve all key requirements, qualifications, responsibilities, and benefits
- Use fresh, original language — do not copy phrases verbatim
- Keep the same job title, company references, and location
- Structure with clear sections: Overview, Responsibilities, Requirements, Nice to Have, Benefits
- Write in a professional, engaging tone
- Output plain text with section headers followed by bullet points using "• "
- Do NOT add any commentary or preamble — just the rewritten job post

Original posting:
{source_text[:4000]}"""

        response = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=2000,
        )
        rewritten = response.choices[0].message.content.strip()
        post.description = rewritten
        post.ai_rewritten = True
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'description': rewritten})
    except Exception as e:
        logger.error('Groq rewrite error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@job_board_bp.post('/admin/fetch')
def admin_fetch():
    data = request.json or {}
    sources = data.get('sources', ['remotive', 'arbeitnow', 'remoteok'])
    search = data.get('search', '')
    limit = int(data.get('limit_per_source', 15))

    adzuna_id = Setting.get('adzuna_app_id', '')
    adzuna_key = Setting.get('adzuna_app_key', '')

    try:
        from utils.job_aggregator import aggregate
        posts_data = aggregate(
            sources=sources,
            search=search,
            limit_per_source=limit,
            adzuna_app_id=adzuna_id or None,
            adzuna_app_key=adzuna_key or None,
        )
    except Exception as e:
        logger.error('Aggregation error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500

    added = 0
    skipped = 0
    for p in posts_data:
        ext_id = p.get('external_id', '')
        if ext_id and JobPost.query.filter_by(external_id=ext_id).first():
            skipped += 1
            continue
        desc = p.get('original_description', '')
        post = JobPost(
            external_id=ext_id,
            source=p.get('source', 'unknown'),
            title=p.get('title', ''),
            company=p.get('company', ''),
            location=p.get('location', ''),
            job_type=p.get('job_type', ''),
            salary=p.get('salary', ''),
            tags=p.get('tags', ''),
            apply_url=p.get('apply_url', ''),
            original_description=desc,
            description=desc,
            status='draft',
        )
        db.session.add(post)
        added += 1

    db.session.commit()
    return jsonify({'success': True, 'added': added, 'skipped': skipped, 'total': len(posts_data)})

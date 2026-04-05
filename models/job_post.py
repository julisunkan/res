from datetime import datetime
from app import db


def _c1(v):
    """Clean a single-line text field."""
    if not v:
        return v
    from utils.job_aggregator import clean_text
    return clean_text(v, multiline=False)


def _cm(v):
    """Clean a multi-line text field."""
    if not v:
        return v
    from utils.job_aggregator import clean_text
    return clean_text(v, multiline=True)


class JobPost(db.Model):
    __tablename__ = 'job_post'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(200))
    source = db.Column(db.String(100), default='manual')
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    job_type = db.Column(db.String(80))
    salary = db.Column(db.String(150))
    tags = db.Column(db.String(500))
    apply_url = db.Column(db.String(800))
    original_description = db.Column(db.Text)
    description = db.Column(db.Text)
    ai_rewritten = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='draft')
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        raw_tags = self.tags or ''
        tag_list = [_c1(t.strip()) for t in raw_tags.split(',') if t.strip()] if raw_tags else []
        desc = _cm(self.description or self.original_description)
        return {
            'id': self.id,
            'source': _c1(self.source),
            'title': _c1(self.title),
            'company': _c1(self.company),
            'location': _c1(self.location),
            'job_type': _c1(self.job_type),
            'salary': _c1(self.salary),
            'tags': tag_list,
            'apply_url': _c1(self.apply_url),
            'description': desc,
            'ai_rewritten': self.ai_rewritten,
            'status': self.status,
            'featured': self.featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

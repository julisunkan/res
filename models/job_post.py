from datetime import datetime
from app import db


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
        return {
            'id': self.id,
            'source': self.source,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'job_type': self.job_type,
            'salary': self.salary,
            'tags': self.tags.split(',') if self.tags else [],
            'apply_url': self.apply_url,
            'description': self.description or self.original_description,
            'ai_rewritten': self.ai_rewritten,
            'status': self.status,
            'featured': self.featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

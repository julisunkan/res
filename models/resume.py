from datetime import datetime
from extensions import db


class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False, default='My Resume')
    original_text = db.Column(db.Text)
    optimized_text = db.Column(db.Text)
    cover_letter = db.Column(db.Text)
    match_score = db.Column(db.Float, default=0.0)
    missing_keywords = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'original_text': self.original_text,
            'optimized_text': self.optimized_text,
            'cover_letter': self.cover_letter,
            'match_score': self.match_score,
            'missing_keywords': self.missing_keywords,
            'suggestions': self.suggestions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

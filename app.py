import os
from flask import Flask, render_template
from flask_cors import CORS
from extensions import db


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from routes.resume import resume_bp
    from routes.jobs import jobs_bp
    from routes.interview import interview_bp
    from routes.chat import chat_bp
    from routes.linkedin import linkedin_bp

    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(linkedin_bp, url_prefix='/api/linkedin')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/resume-builder')
    def resume_builder():
        return render_template('resume_builder.html')

    @app.route('/job-tracker')
    def job_tracker():
        return render_template('job_tracker.html')

    @app.route('/interview-prep')
    def interview_prep():
        return render_template('interview_prep.html')

    @app.route('/career-chat')
    def career_chat():
        return render_template('career_chat.html')

    @app.route('/linkedin-optimizer')
    def linkedin_optimizer():
        return render_template('linkedin_optimizer.html')

    with app.app_context():
        import models.resume
        import models.job
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

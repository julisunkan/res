import os
from datetime import timedelta
from flask import Flask, render_template
from flask_cors import CORS
from extensions import db


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'julisunkan-super-secret-key-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from routes.resume import resume_bp
    from routes.jobs import jobs_bp
    from routes.interview import interview_bp
    from routes.chat import chat_bp
    from routes.linkedin import linkedin_bp
    from routes.admin import admin_bp

    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(linkedin_bp, url_prefix='/api/linkedin')
    app.register_blueprint(admin_bp, url_prefix='/julisunkan')

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

    @app.route('/privacy-policy')
    def privacy_policy():
        return render_template('privacy.html')

    @app.route('/terms-of-service')
    def terms_of_service():
        return render_template('terms.html')

    @app.route('/cookie-policy')
    def cookie_policy():
        return render_template('cookie_policy.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/ads.txt')
    def ads_txt():
        from flask import Response
        from models.settings import Setting
        content = Setting.get('ads_txt_content', '')
        return Response(content, mimetype='text/plain')

    @app.context_processor
    def inject_site_settings():
        from datetime import datetime
        try:
            from models.settings import Setting
            return dict(
                site_analytics_id=Setting.get('analytics_id', ''),
                site_adsense_id=Setting.get('adsense_publisher_id', ''),
                site_app_name=Setting.get('app_name', 'AI Resume & Cover Letter Creator'),
                current_year=datetime.utcnow().year,
            )
        except Exception:
            return dict(site_analytics_id='', site_adsense_id='', site_app_name='AI Resume & Cover Letter Creator', current_year=datetime.utcnow().year)

    with app.app_context():
        import models.resume
        import models.job
        import models.settings
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

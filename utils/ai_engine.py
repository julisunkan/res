import os
from groq import Groq

_client = None


def _get_api_key():
    """Get API key: env var first, then database settings."""
    key = os.environ.get('GROQ_API_KEY', '')
    if not key:
        try:
            from models.settings import Setting
            key = Setting.get('groq_api_key', '')
        except Exception:
            pass
    return key


DEFAULT_MODEL = 'llama-3.3-70b-versatile'

# Models that are no longer supported by Groq
DEPRECATED_MODELS = {
    'llama3-70b-8192', 'llama3-8b-8192',
    'mixtral-8x7b-32768', 'gemma2-9b-it',
    'gemma-7b-it', 'llama2-70b-4096',
}

def _get_model():
    try:
        from models.settings import Setting
        model = Setting.get('ai_model', DEFAULT_MODEL) or DEFAULT_MODEL
        if model in DEPRECATED_MODELS:
            Setting.set('ai_model', DEFAULT_MODEL)
            return DEFAULT_MODEL
        return model
    except Exception:
        return DEFAULT_MODEL


def _get_max_tokens():
    try:
        from models.settings import Setting
        val = Setting.get('ai_max_tokens', '4096')
        return int(val) if val else 4096
    except Exception:
        return 4096


def get_client():
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("No Groq API key configured. Please add it in the Admin Panel at /julisunkan")
    return Groq(api_key=api_key)


def ai_generate(system_prompt, user_prompt, max_tokens=None, temperature=0.7):
    client = get_client()
    if max_tokens is None:
        max_tokens = _get_max_tokens()
    response = client.chat.completions.create(
        model=_get_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def optimize_resume(resume_text, job_description):
    system = (
        "You are an expert ATS resume optimizer and career coach. "
        "Your task is to rewrite and optimize the provided resume to match the job description. "
        "Make it ATS-friendly, keyword-rich, and impactful. "
        "Return ONLY the optimized resume text, no commentary."
    )
    user = f"RESUME:\n{resume_text[:3000]}\n\nJOB DESCRIPTION:\n{job_description[:2000]}\n\nOptimize the resume to match this job description. Make it ATS-friendly."
    return ai_generate(system, user)


def generate_cover_letter(resume_text, job_description):
    system = (
        "You are a professional cover letter writer. "
        "Write a compelling, personalized cover letter based on the resume and job description. "
        "Return ONLY the cover letter text, no commentary."
    )
    user = f"RESUME:\n{resume_text[:2000]}\n\nJOB DESCRIPTION:\n{job_description[:2000]}\n\nWrite a tailored cover letter."
    return ai_generate(system, user)


def analyze_match(resume_text, job_description):
    system = (
        "You are a resume-job match analyzer. Analyze the resume against the job description and return a JSON object with these fields:\n"
        "- score: number from 0-100 (match percentage)\n"
        "- missing_keywords: array of important keywords from job description missing in resume\n"
        "- suggestions: array of specific improvement suggestions\n"
        "Return ONLY valid JSON, no markdown, no commentary."
    )
    user = f"RESUME:\n{resume_text[:2500]}\n\nJOB DESCRIPTION:\n{job_description[:1500]}\n\nAnalyze the match and return JSON."
    return ai_generate(system, user, max_tokens=1000)


def rewrite_section(section_text, section_name, job_description):
    system = (
        "You are an expert resume writer. Rewrite the given resume section to be more impactful, "
        "quantified, and relevant to the job description. "
        "Return ONLY the rewritten section, no commentary."
    )
    user = f"SECTION ({section_name}):\n{section_text[:1500]}\n\nJOB DESCRIPTION:\n{job_description[:1000]}\n\nRewrite this section."
    return ai_generate(system, user, max_tokens=800)


def generate_interview_questions(job_description):
    system = (
        "You are an interview preparation expert. Generate 10 likely interview questions based on the job description. "
        "For each question, also provide a sample answer. "
        "Return a JSON array of objects with 'question' and 'sample_answer' fields. "
        "Return ONLY valid JSON array."
    )
    user = f"JOB DESCRIPTION:\n{job_description[:2000]}\n\nGenerate 10 interview questions with sample answers."
    return ai_generate(system, user, max_tokens=3000)


def analyze_job_description(job_description):
    system = (
        "You are a job description analyzer. Analyze the job description and return a JSON object with:\n"
        "- required_skills: array of required technical and soft skills\n"
        "- keywords: array of important ATS keywords\n"
        "- experience_level: string (entry/junior/mid/senior/lead)\n"
        "- key_responsibilities: array of main responsibilities\n"
        "Return ONLY valid JSON."
    )
    user = f"JOB DESCRIPTION:\n{job_description[:2500]}\n\nAnalyze and return JSON."
    return ai_generate(system, user, max_tokens=1500)


def chat_with_career_assistant(messages):
    system = (
        "You are an expert AI career assistant. You help users with resume writing, job searching, "
        "interview preparation, career advice, salary negotiation, and professional development. "
        "Be helpful, specific, and encouraging."
    )
    client = get_client()
    all_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=_get_model(),
        messages=all_messages,
        max_tokens=1500,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def optimize_linkedin_profile(headline, about, job_title, industry):
    system = (
        "You are a LinkedIn profile optimization expert. "
        "Improve the LinkedIn headline and About section to be more compelling and keyword-rich. "
        "Return a JSON object with 'headline' and 'about' fields. "
        "Return ONLY valid JSON."
    )
    user = f"CURRENT HEADLINE: {headline}\nCURRENT ABOUT: {about[:1000]}\nTARGET JOB TITLE: {job_title}\nINDUSTRY: {industry}\n\nOptimize the LinkedIn profile."
    return ai_generate(system, user, max_tokens=800)


def rewrite_job_description(title: str, company: str, raw_description: str) -> str:
    """
    Rewrite a raw job description into a clean, structured, professional posting.
    Returns the rewritten text (plain text with section headers + bullet points).
    Raises on failure so callers can decide whether to fall back to the original.
    """
    system = (
        "You are a professional job description writer. "
        "Your task is to rewrite raw job postings into clean, well-structured, engaging descriptions. "
        "Rules:\n"
        "- Preserve all factual details: requirements, responsibilities, salary, benefits, apply link\n"
        "- Use fresh, original language — do not copy phrases verbatim\n"
        "- Structure output with these sections (only include sections that have content):\n"
        "  About the Role, Key Responsibilities, Requirements, Nice to Have, Benefits\n"
        "- Use bullet points (• ) for list items\n"
        "- Write in a professional, engaging tone — no fluff, no filler\n"
        "- Output plain text only — no markdown, no HTML, no code fences\n"
        "- Do NOT add any preamble or commentary — just the rewritten job post"
    )
    user = (
        f"Job Title: {title}\n"
        f"Company: {company}\n\n"
        f"Raw description:\n{raw_description[:3500]}\n\n"
        "Rewrite this job posting following the rules above."
    )
    return ai_generate(system, user, max_tokens=1200, temperature=0.6)


def generate_resume_from_skills(name, skills, education, experience_notes):
    system = (
        "You are an expert resume writer specializing in helping students and career changers. "
        "Create a professional resume from the provided information. Focus on skills, education, projects, and potential. "
        "Return ONLY the resume text in a clean, professional format."
    )
    user = f"NAME: {name}\nSKILLS: {skills}\nEDUCATION: {education}\nEXPERIENCE/NOTES: {experience_notes}\n\nCreate a professional resume."
    return ai_generate(system, user, max_tokens=2000)

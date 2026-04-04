import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; AIResumeBot/1.0)'}
TIMEOUT = 15


def _strip_html(html: str) -> str:
    if not html:
        return ''
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(p|div|h[1-6]|ul|ol|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-z]+;', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_remotive(search='', limit=20):
    posts = []
    try:
        params = {'limit': limit}
        if search:
            params['search'] = search
        resp = requests.get('https://remotive.com/api/remote-jobs', params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get('jobs', []):
            tags = ', '.join(j.get('tags', []))
            job_type = j.get('job_type', 'remote').replace('_', '-')
            posts.append({
                'source': 'remotive',
                'external_id': 'remotive-' + str(j.get('id', '')),
                'title': j.get('title', ''),
                'company': j.get('company_name', ''),
                'location': j.get('candidate_required_location') or 'Remote',
                'job_type': job_type,
                'salary': j.get('salary', ''),
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': _strip_html(j.get('description', '')),
            })
    except Exception as e:
        logger.warning('Remotive fetch error: %s', e)
    return posts


def fetch_arbeitnow(limit=20):
    posts = []
    try:
        resp = requests.get('https://arbeitnow.com/api/job-board-api', headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get('data', [])[:limit]:
            tags = ', '.join(j.get('tags', []))
            job_types = j.get('job_types', [])
            job_type = job_types[0] if job_types else ('remote' if j.get('remote') else 'full-time')
            posts.append({
                'source': 'arbeitnow',
                'external_id': 'arbeitnow-' + str(j.get('slug', '')),
                'title': j.get('title', ''),
                'company': j.get('company_name', ''),
                'location': j.get('location') or ('Remote' if j.get('remote') else ''),
                'job_type': job_type,
                'salary': '',
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': _strip_html(j.get('description', '')),
            })
    except Exception as e:
        logger.warning('Arbeitnow fetch error: %s', e)
    return posts


def fetch_remoteok(limit=20):
    posts = []
    try:
        resp = requests.get('https://remoteok.com/api', headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        jobs = [j for j in data if isinstance(j, dict) and j.get('id')]
        for j in jobs[:limit]:
            tags = ', '.join(j.get('tags', []))
            salary_min = j.get('salary_min')
            salary_max = j.get('salary_max')
            salary = ''
            if salary_min and salary_max:
                salary = f'${salary_min:,} – ${salary_max:,}'
            elif salary_min:
                salary = f'${salary_min:,}+'
            posts.append({
                'source': 'remoteok',
                'external_id': 'remoteok-' + str(j.get('id', '')),
                'title': j.get('position', j.get('title', '')),
                'company': j.get('company', ''),
                'location': j.get('location') or 'Remote',
                'job_type': 'remote',
                'salary': salary,
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': _strip_html(j.get('description', '')),
            })
    except Exception as e:
        logger.warning('RemoteOK fetch error: %s', e)
    return posts


def fetch_adzuna(app_id, app_key, query='developer', country='us', limit=20):
    posts = []
    try:
        url = f'https://api.adzuna.com/v1/api/jobs/{country}/search/1'
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': min(limit, 50),
            'what': query,
            'content-type': 'application/json',
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get('results', []):
            posts.append({
                'source': 'adzuna',
                'external_id': 'adzuna-' + str(j.get('id', '')),
                'title': j.get('title', ''),
                'company': j.get('company', {}).get('display_name', ''),
                'location': j.get('location', {}).get('display_name', ''),
                'job_type': j.get('contract_time', 'full-time').replace('_', '-'),
                'salary': '',
                'tags': j.get('category', {}).get('label', ''),
                'apply_url': j.get('redirect_url', ''),
                'original_description': _strip_html(j.get('description', '')),
            })
    except Exception as e:
        logger.warning('Adzuna fetch error: %s', e)
    return posts


def aggregate(sources=None, search='', limit_per_source=15, adzuna_app_id=None, adzuna_app_key=None):
    if sources is None:
        sources = ['remotive', 'arbeitnow', 'remoteok']
    all_posts = []
    if 'remotive' in sources:
        all_posts.extend(fetch_remotive(search=search, limit=limit_per_source))
    if 'arbeitnow' in sources:
        all_posts.extend(fetch_arbeitnow(limit=limit_per_source))
    if 'remoteok' in sources:
        all_posts.extend(fetch_remoteok(limit=limit_per_source))
    if 'adzuna' in sources and adzuna_app_id and adzuna_app_key:
        all_posts.extend(fetch_adzuna(adzuna_app_id, adzuna_app_key, query=search or 'developer', limit=limit_per_source))
    return all_posts

import html as html_mod
import logging
import re
import unicodedata
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
}
TIMEOUT = 15


def clean_text(text: str, multiline: bool = True) -> str:
    """
    Thoroughly clean a string of text coming from external job APIs:
      - Decode all HTML entities (named, decimal & hex: &amp; &#38; &#x26;)
      - Strip all HTML / XML tags
      - Replace non-breaking spaces and other exotic whitespace with a plain space
      - Remove zero-width / invisible Unicode characters
      - Remove ASCII and Unicode control characters (keep \\n and \\t)
      - NFKC-normalise (folds ligatures, full-width chars, etc.)
      - Collapse runs of blank lines (multiline) or all whitespace (single-line)
    """
    if not text:
        return ''

    # 1. Decode HTML entities iteratively (some content is double-escaped)
    prev = None
    while prev != text:
        prev = text
        text = html_mod.unescape(text)

    # 2. Replace block-level HTML tags with newlines, inline tags with spaces
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(
        r'</?(p|div|h[1-6]|ul|ol|tr|thead|tbody|table|section|article|header|footer|blockquote)[^>]*>',
        '\n', text, flags=re.IGNORECASE,
    )
    text = re.sub(r'<[^>]+>', ' ', text)  # remaining tags → space

    # 3. NFKC normalisation (handles full-width chars, ligatures, etc.)
    text = unicodedata.normalize('NFKC', text)

    # 4. Replace all exotic whitespace variants with a plain space
    # Covers: non-breaking space \xa0, thin space, hair space, zero-width no-break
    # space \ufeff, en/em space, ideographic space, etc.
    text = re.sub(
        r'[\xa0\u00ad\u180e\u200b\u200c\u200d\u2028\u2029\u202f\u205f\u2060\ufeff\u00a0]',
        ' ', text,
    )
    # Any remaining Unicode "space separator" category
    text = re.sub(r'\u3000', ' ', text)  # ideographic space

    # 5. Remove control characters except \n and \t
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Remove Unicode control / private-use / surrogate ranges
    text = re.sub(r'[\u0080-\u009f\ue000-\uf8ff]', '', text)

    # 6. Collapse inline whitespace (spaces/tabs) to a single space per line
    if multiline:
        lines = text.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in lines]
        # Collapse runs of more than 2 consecutive blank lines
        cleaned_lines = []
        blank_count = 0
        for ln in lines:
            if ln == '':
                blank_count += 1
                if blank_count <= 1:
                    cleaned_lines.append(ln)
            else:
                blank_count = 0
                cleaned_lines.append(ln)
        text = '\n'.join(cleaned_lines).strip()
    else:
        # Single-line field: collapse all whitespace to one space
        text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_job(data: dict) -> dict:
    """Apply clean_text to all text fields of a job dict."""
    single = ('title', 'company', 'location', 'job_type', 'salary', 'apply_url', 'source', 'external_id')
    multi  = ('original_description', 'description')
    result = dict(data)
    for field in single:
        if field in result and result[field]:
            result[field] = clean_text(str(result[field]), multiline=False)
    for field in multi:
        if field in result and result[field]:
            result[field] = clean_text(str(result[field]), multiline=True)
    # Tags: clean each tag individually, re-join
    if result.get('tags'):
        raw_tags = result['tags']
        tag_list = raw_tags if isinstance(raw_tags, list) else [t.strip() for t in raw_tags.split(',')]
        result['tags'] = ', '.join(clean_text(t, multiline=False) for t in tag_list if t.strip())
    return result


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
            posts.append(clean_job({
                'source': 'remotive',
                'external_id': 'remotive-' + str(j.get('id', '')),
                'title': j.get('title', ''),
                'company': j.get('company_name', ''),
                'location': j.get('candidate_required_location') or 'Remote',
                'job_type': job_type,
                'salary': j.get('salary', ''),
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': clean_text(j.get('description', ''), multiline=True),
            }))
    except Exception as e:
        logger.warning('Remotive fetch error: %s', e)
    return posts


def fetch_arbeitnow(limit=20):
    """Try multiple Arbeitnow endpoints; silently skip if all fail."""
    posts = []
    urls = [
        'https://arbeitnow.com/api/job-board-api',
        'https://www.arbeitnow.com/api/job-board-api',
    ]
    resp = None
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                resp = r
                break
        except Exception:
            pass

    if resp is None:
        logger.debug('Arbeitnow unavailable (all endpoints failed or returned non-200)')
        return posts

    try:
        data = resp.json()
        for j in data.get('data', [])[:limit]:
            tags = ', '.join(j.get('tags', []))
            job_types = j.get('job_types', [])
            job_type = job_types[0] if job_types else ('remote' if j.get('remote') else 'full-time')
            posts.append(clean_job({
                'source': 'arbeitnow',
                'external_id': 'arbeitnow-' + str(j.get('slug', '')),
                'title': j.get('title', ''),
                'company': j.get('company_name', ''),
                'location': j.get('location') or ('Remote' if j.get('remote') else ''),
                'job_type': job_type,
                'salary': '',
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': clean_text(j.get('description', ''), multiline=True),
            }))
    except Exception as e:
        logger.warning('Arbeitnow parse error: %s', e)
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
                salary = f'${salary_min:,} \u2013 ${salary_max:,}'
            elif salary_min:
                salary = f'${salary_min:,}+'
            posts.append(clean_job({
                'source': 'remoteok',
                'external_id': 'remoteok-' + str(j.get('id', '')),
                'title': j.get('position', j.get('title', '')),
                'company': j.get('company', ''),
                'location': j.get('location') or 'Remote',
                'job_type': 'remote',
                'salary': salary,
                'tags': tags,
                'apply_url': j.get('url', ''),
                'original_description': clean_text(j.get('description', ''), multiline=True),
            }))
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
            posts.append(clean_job({
                'source': 'adzuna',
                'external_id': 'adzuna-' + str(j.get('id', '')),
                'title': j.get('title', ''),
                'company': j.get('company', {}).get('display_name', ''),
                'location': j.get('location', {}).get('display_name', ''),
                'job_type': j.get('contract_time', 'full-time').replace('_', '-'),
                'salary': '',
                'tags': j.get('category', {}).get('label', ''),
                'apply_url': j.get('redirect_url', ''),
                'original_description': clean_text(j.get('description', ''), multiline=True),
            }))
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

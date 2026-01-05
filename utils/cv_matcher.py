"""
CV Version Matcher - Smart matching algorithm for CV versions against job descriptions.

Considers:
- Role title similarity
- Skills overlap
- Category alignment
- Historical performance (response rate)
"""
import logging
import re
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)

# Common skill keywords by category
SKILL_CATEGORIES = {
    'programming_languages': [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql'
    ],
    'frameworks': [
        'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring',
        'express', 'node.js', 'nodejs', '.net', 'rails', 'laravel', 'nextjs'
    ],
    'cloud': [
        'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s',
        'terraform', 'cloudformation', 'serverless', 'lambda', 'ec2', 's3'
    ],
    'data': [
        'machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning',
        'data science', 'data engineering', 'etl', 'spark', 'hadoop', 'airflow',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn'
    ],
    'databases': [
        'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'dynamodb', 'cassandra', 'oracle', 'sql server', 'sqlite'
    ],
    'devops': [
        'ci/cd', 'jenkins', 'github actions', 'gitlab', 'ansible', 'puppet',
        'chef', 'prometheus', 'grafana', 'elk', 'splunk', 'datadog'
    ],
    'soft_skills': [
        'leadership', 'management', 'agile', 'scrum', 'communication',
        'team lead', 'project management', 'stakeholder', 'cross-functional'
    ]
}

# Role category mappings
ROLE_CATEGORIES = {
    'software_engineer': ['software engineer', 'developer', 'programmer', 'sde', 'backend', 'frontend', 'fullstack'],
    'data_engineer': ['data engineer', 'data analyst', 'business intelligence', 'bi developer', 'etl'],
    'data_scientist': ['data scientist', 'machine learning', 'ml engineer', 'ai engineer', 'research scientist'],
    'devops': ['devops', 'sre', 'site reliability', 'platform engineer', 'infrastructure'],
    'architect': ['architect', 'technical lead', 'principal engineer', 'staff engineer'],
    'manager': ['engineering manager', 'tech lead', 'team lead', 'head of', 'director', 'vp of'],
    'product': ['product manager', 'product owner', 'pm', 'program manager'],
    'security': ['security engineer', 'cybersecurity', 'infosec', 'penetration tester']
}


class CVVersionMatcher:
    """Smart matcher for CV versions against job descriptions."""

    def __init__(self):
        # Flatten skill categories for quick lookup
        self.all_skills = set()
        for skills in SKILL_CATEGORIES.values():
            self.all_skills.update(skills)

    def match_versions(
        self,
        versions: List[Dict[str, Any]],
        job_description: str,
        job_title: Optional[str] = None,
        company_name: Optional[str] = None,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Match CV versions against a job description.

        Returns top suggestions with scores and analysis.
        """
        # Analyze the job
        job_analysis = self._analyze_job(job_description, job_title, company_name)

        # Score each version
        scored_versions = []
        for version in versions:
            score_data = self._score_version(version, job_analysis)
            scored_versions.append({
                **score_data,
                'version_id': version.get('version_id'),
                'version_name': version.get('version_name'),
                'auto_category': version.get('auto_category'),
                'usage_count': version.get('usage_count', 0),
                'response_count': version.get('response_count', 0)
            })

        # Sort by overall score descending
        scored_versions.sort(key=lambda x: x['overall_score'], reverse=True)

        return {
            'suggestions': scored_versions[:limit],
            'job_analysis': job_analysis
        }

    def _analyze_job(
        self,
        job_description: str,
        job_title: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze job requirements."""
        text = f"{job_title or ''} {job_description}".lower()

        # Extract skills mentioned
        found_skills = {}
        for category, skills in SKILL_CATEGORIES.items():
            found = [s for s in skills if s in text]
            if found:
                found_skills[category] = found

        # Detect role category
        detected_role = None
        for role_cat, keywords in ROLE_CATEGORIES.items():
            if any(kw in text for kw in keywords):
                detected_role = role_cat
                break

        # Extract seniority level
        seniority = 'mid'
        if any(word in text for word in ['senior', 'sr.', 'lead', 'principal', 'staff']):
            seniority = 'senior'
        elif any(word in text for word in ['junior', 'jr.', 'entry', 'graduate', 'intern']):
            seniority = 'junior'
        elif any(word in text for word in ['head', 'director', 'vp', 'chief', 'manager']):
            seniority = 'executive'

        # Extract years of experience if mentioned
        years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience', text)
        years_required = int(years_match.group(1)) if years_match else None

        return {
            'title': job_title,
            'company': company_name,
            'detected_role': detected_role,
            'seniority': seniority,
            'years_required': years_required,
            'skills_by_category': found_skills,
            'all_skills': [s for skills in found_skills.values() for s in skills]
        }

    def _score_version(
        self,
        version: Dict[str, Any],
        job_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Score a CV version against job analysis."""
        scores = {
            'role_similarity': 0,
            'skills_overlap': 0,
            'category_match': 0,
            'performance_bonus': 0
        }
        reasons = []

        # 1. Role Similarity (based on auto_category and version name)
        version_category = (version.get('auto_category') or '').lower()
        version_name = (version.get('version_name') or '').lower()
        job_role = job_analysis.get('detected_role', '')

        if job_role:
            role_keywords = ROLE_CATEGORIES.get(job_role, [])
            if any(kw in version_category for kw in role_keywords):
                scores['role_similarity'] = 90
                reasons.append(f"Category matches job role: {job_role}")
            elif any(kw in version_name for kw in role_keywords):
                scores['role_similarity'] = 70
                reasons.append(f"Version name suggests {job_role} role")

        # 2. Skills Overlap (based on tags and version name)
        version_tags = version.get('user_tags', '')
        if isinstance(version_tags, str):
            version_tags = [t.strip().lower() for t in version_tags.split(',') if t.strip()]
        else:
            version_tags = [t.lower() for t in version_tags]

        # Add words from version name as pseudo-tags
        name_words = re.findall(r'\b\w+\b', version_name)
        version_tags.extend([w.lower() for w in name_words if len(w) > 2])

        job_skills = set(job_analysis.get('all_skills', []))
        if job_skills:
            matching_skills = job_skills.intersection(set(version_tags))
            if matching_skills:
                overlap_pct = len(matching_skills) / len(job_skills) * 100
                scores['skills_overlap'] = min(overlap_pct * 1.5, 100)  # Boost for partial matches
                reasons.append(f"Skills match: {', '.join(list(matching_skills)[:3])}")

        # 3. Category Match (exact category alignment)
        if version_category and job_role:
            if version_category == job_role:
                scores['category_match'] = 100
            elif any(kw in version_category for kw in ROLE_CATEGORIES.get(job_role, [])):
                scores['category_match'] = 75

        # 4. Performance Bonus (historical success rate)
        usage = version.get('usage_count', 0)
        responses = version.get('response_count', 0)
        if usage >= 3:
            response_rate = responses / usage * 100
            scores['performance_bonus'] = min(response_rate * 0.5, 25)  # Max 25% bonus
            if response_rate > 30:
                reasons.append(f"High response rate: {response_rate:.0f}%")

        # Calculate overall score (weighted average)
        weights = {
            'role_similarity': 0.35,
            'skills_overlap': 0.35,
            'category_match': 0.15,
            'performance_bonus': 0.15
        }

        overall = sum(scores[k] * weights[k] for k in weights)

        # Calculate response rate for display
        response_rate = 0
        if usage > 0:
            response_rate = responses / usage * 100

        return {
            'overall_score': round(overall, 1),
            'role_similarity': round(scores['role_similarity'], 1),
            'skills_overlap': round(scores['skills_overlap'], 1),
            'response_rate': round(response_rate, 1),
            'reasons': reasons
        }


def detect_role_category(text: str) -> Optional[str]:
    """Detect the role category from text (job description or CV content)."""
    text_lower = text.lower()
    for role_cat, keywords in ROLE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return role_cat
    return None


def extract_skills(text: str) -> List[str]:
    """Extract recognized skills from text."""
    text_lower = text.lower()
    found = []
    for category, skills in SKILL_CATEGORIES.items():
        for skill in skills:
            if skill in text_lower:
                found.append(skill)
    return list(set(found))

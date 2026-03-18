"""
HR (Human Resources) Resume Scorer

Simulates human HR recruiter evaluation logic beyond ATS keyword matching.
Evaluates career narrative, trajectory, impact signals, and red flags.

Components:
- Years of experience extraction and alignment
- Career trajectory/progression signals
- Skills coverage percentage
- Role title similarity
- Impact/achievement signals (numbers, percentages, verbs)

Ported from Resume-Builder, adapted for WinningCV.
No SBERT/semantic similarity - pure rule-based scoring.
"""

import re
import math
from datetime import datetime, date
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any


# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

# Title hierarchy mapping for trajectory scoring (1-9 scale)
TITLE_HIERARCHY = {
    # Entry Level (1-2)
    'intern': 1, 'trainee': 1, 'apprentice': 1,
    'assistant': 2, 'associate': 2, 'junior': 2, 'entry': 2,
    'coordinator': 2, 'administrator': 2,

    # Mid Level (3-4)
    'analyst': 3, 'specialist': 3, 'engineer': 3, 'developer': 3,
    'consultant': 3, 'officer': 3, 'representative': 3,
    'senior analyst': 4, 'senior specialist': 4, 'senior engineer': 4,
    'senior': 4, 'lead': 4, 'principal': 4, 'staff': 4,

    # Management (5-6)
    'supervisor': 5, 'team lead': 5, 'manager': 5, 'program manager': 5,
    'project manager': 5, 'product manager': 5,
    'senior manager': 6, 'associate director': 6, 'director': 6,
    'head': 6, 'head of': 6,

    # Executive (7-9)
    'senior director': 7, 'vice president': 7, 'vp': 7,
    'senior vice president': 8, 'svp': 8, 'evp': 8,
    'chief': 9, 'ceo': 9, 'cfo': 9, 'cto': 9, 'coo': 9, 'cmo': 9,
    'president': 9, 'partner': 8, 'managing director': 8,
}

# Strong action verbs by category (Bloom's Taxonomy inspired)
STRONG_ACTION_VERBS = {
    'leadership': [
        'led', 'directed', 'managed', 'headed', 'spearheaded', 'oversaw',
        'supervised', 'orchestrated', 'championed', 'pioneered', 'established',
        'founded', 'launched', 'initiated', 'drove', 'transformed'
    ],
    'achievement': [
        'achieved', 'exceeded', 'surpassed', 'delivered', 'generated',
        'increased', 'improved', 'reduced', 'saved', 'accelerated',
        'optimized', 'maximized', 'doubled', 'tripled', 'grew'
    ],
    'technical': [
        'developed', 'designed', 'engineered', 'built', 'created',
        'implemented', 'deployed', 'architected', 'automated', 'integrated',
        'programmed', 'coded', 'configured', 'migrated', 'scaled'
    ],
    'analytical': [
        'analyzed', 'evaluated', 'assessed', 'investigated', 'researched',
        'identified', 'discovered', 'diagnosed', 'validated', 'verified',
        'quantified', 'measured', 'tracked', 'monitored', 'audited'
    ],
    'collaborative': [
        'collaborated', 'partnered', 'coordinated', 'facilitated', 'negotiated',
        'liaised', 'aligned', 'unified', 'bridged', 'integrated'
    ]
}

# Weak/passive verbs to penalize
WEAK_VERBS = [
    'responsible for', 'duties included', 'helped', 'assisted', 'participated',
    'was involved', 'worked on', 'handled', 'dealt with', 'tasked with'
]

# AI cliché verbs (overused in AI-generated resumes)
AI_CLICHE_VERBS = {
    'spearheaded', 'leveraged', 'utilized', 'facilitated', 'ensured',
    'demonstrated', 'streamlined', 'championed', 'fostered', 'harnessed',
    'navigated', 'liaised', 'interfaced',
    'spearhead', 'leverage', 'utilize', 'facilitate', 'ensure',
    'demonstrate', 'streamline', 'champion', 'foster', 'harness',
    'spearheading', 'leveraging', 'utilizing', 'facilitating', 'ensuring',
}

# Gap explanations that reduce penalty
GAP_EXPLANATIONS = [
    'parental leave', 'maternity leave', 'paternity leave', 'family leave',
    'sabbatical', 'caregiving', 'caregiver', 'medical leave', 'health',
    'relocation', 'immigration', 'visa', 'travel', 'study', 'education',
    'graduate school', 'mba', 'certification', 'training', 'bootcamp',
    'startup', 'entrepreneur', 'freelance', 'consulting', 'contract'
]

# Weight profiles based on seniority
WEIGHT_PROFILES = {
    'junior': {
        'experience': 0.15,
        'skills': 0.30,
        'trajectory': 0.10,
        'impact': 0.20,
        'title_match': 0.25,
    },
    'mid': {
        'experience': 0.20,
        'skills': 0.25,
        'trajectory': 0.15,
        'impact': 0.20,
        'title_match': 0.20,
    },
    'senior': {
        'experience': 0.25,
        'skills': 0.20,
        'trajectory': 0.15,
        'impact': 0.20,
        'title_match': 0.20,
    },
    'executive': {
        'experience': 0.20,
        'skills': 0.15,
        'trajectory': 0.20,
        'impact': 0.25,
        'title_match': 0.20,
    },
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class JobEntry:
    """Represents a single job/position from resume."""
    title: str
    company: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None  # None = Present
    bullets: List[str] = field(default_factory=list)
    duration_months: int = 0
    hierarchy_level: int = 3  # Default mid-level
    is_current: bool = False


@dataclass
class ExperienceAnalysis:
    """Analysis of candidate experience."""
    total_years: float
    required_years: float
    alignment_score: float
    assessment: str


@dataclass
class TrajectoryAnalysis:
    """Analysis of career trajectory."""
    score: float
    direction: str  # 'ascending', 'stable', 'descending'
    annual_slope: float
    narrative: str


@dataclass
class ImpactAnalysis:
    """Analysis of impact/achievement signals."""
    score: float
    metrics_count: int
    strong_verbs_count: int
    weak_verbs_count: int
    metrics_density: float
    verb_power_index: float


@dataclass
class SkillsCoverage:
    """Analysis of skills coverage."""
    score: float
    matched: List[str]
    missing: List[str]
    coverage_rate: float


@dataclass
class TitleMatchAnalysis:
    """Analysis of role title similarity."""
    score: float
    resume_level: int
    target_level: int
    assessment: str


@dataclass
class HRScoreResult:
    """Complete HR scoring result."""
    overall_score: float
    recommendation: str  # INTERVIEW, MAYBE, PASS
    rating_label: str
    confidence: str

    experience_score: float
    skills_score: float
    trajectory_score: float
    impact_score: float
    title_match_score: float

    strengths: List[str]
    concerns: List[str]
    suggested_questions: List[str]

    penalties_applied: Dict[str, float]
    weights_used: Dict[str, float]
    breakdown: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_score': round(self.overall_score, 1),
            'recommendation': self.recommendation,
            'rating_label': self.rating_label,
            'confidence': self.confidence,
            'factor_breakdown': {
                'experience': round(self.experience_score, 1),
                'skills': round(self.skills_score, 1),
                'trajectory': round(self.trajectory_score, 1),
                'impact': round(self.impact_score, 1),
                'title_match': round(self.title_match_score, 1),
            },
            'strengths': self.strengths[:5],
            'concerns': self.concerns[:5],
            'suggested_questions': self.suggested_questions[:4],
            'penalties_applied': self.penalties_applied,
            'weights_used': {k: round(v, 2) for k, v in self.weights_used.items()},
            'breakdown': self.breakdown,
        }


# =============================================================================
# TEXT PROCESSING & PARSING
# =============================================================================

def parse_date(date_str: str) -> Optional[date]:
    """Parse various date formats to date object."""
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    # Handle "Present", "Current", etc.
    if any(word in date_str for word in ['present', 'current', 'now', 'ongoing']):
        return None  # None represents "Present"

    # Common date patterns
    patterns = [
        (r'(\w+)\s+(\d{4})', '%B %Y'),  # "January 2024"
        (r'(\w{3})\s+(\d{4})', '%b %Y'),  # "Jan 2024"
        (r'(\d{1,2})/(\d{4})', '%m/%Y'),  # "01/2024"
        (r'(\d{4})', '%Y'),  # "2024"
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                if fmt == '%Y':
                    return date(int(match.group(1)), 6, 1)  # Assume mid-year
                else:
                    parsed = datetime.strptime(match.group(0), fmt)
                    return parsed.date()
            except ValueError:
                continue

    return None


def extract_years_from_text(text: str) -> Optional[float]:
    """Extract years of experience from text like '5+ years'."""
    patterns = [
        r'minimum\s*(?:of\s+)?(\d+)\s*(?:years?|yrs?)',
        r'at\s+least\s+(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',
        r'(\d+)\+?\s*(?:years?|yrs?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            years = float(match.group(1))
            if years <= 20:  # Sanity check
                return years

    return None


def determine_seniority_level(text: str) -> str:
    """Determine job seniority level from text."""
    text_lower = text.lower()

    if any(term in text_lower for term in ['chief', 'vp', 'vice president', 'c-level', 'executive']):
        return 'executive'

    if any(term in text_lower for term in ['director', 'senior manager', 'head of', 'principal']):
        return 'senior'

    if any(term in text_lower for term in ['senior', 'lead', 'sr.', 'experienced']):
        return 'mid'

    if any(term in text_lower for term in ['entry', 'junior', 'associate', 'graduate', 'trainee']):
        return 'junior'

    # Default based on years required
    years = extract_years_from_text(text)
    if years:
        if years >= 10:
            return 'senior'
        elif years >= 5:
            return 'mid'
        else:
            return 'junior'

    return 'mid'


def get_title_hierarchy_level(title: str) -> int:
    """Map job title to hierarchy level (1-9)."""
    title_lower = title.lower().strip()

    # Direct lookup
    for key, level in TITLE_HIERARCHY.items():
        if key in title_lower:
            return level

    return 3  # Default to mid-level


def extract_bullets_from_text(text: str) -> List[str]:
    """Extract bullet points from resume text."""
    bullets = []
    lines = text.split('\n')

    bullet_patterns = [r'^\s*[•\-\*\◦\▪]\s*(.+)', r'^\s*\d+\.\s*(.+)']

    for line in lines:
        line = line.strip()
        for pattern in bullet_patterns:
            match = re.match(pattern, line)
            if match:
                bullets.append(match.group(1).strip())
                break

    # Also include lines that look like achievements but without bullets
    if len(bullets) < 5:
        for line in lines:
            line = line.strip()
            if len(line) > 30 and any(verb in line.lower() for category in STRONG_ACTION_VERBS.values() for verb in category):
                if line not in bullets:
                    bullets.append(line)

    return bullets


def extract_jobs_from_text(text: str) -> List[JobEntry]:
    """Extract job entries from resume text (simplified parsing)."""
    jobs = []
    lines = text.split('\n')

    # Pattern for job titles/companies
    title_pattern = re.compile(
        r'^([A-Z][A-Za-z\s]+(?:Manager|Engineer|Developer|Analyst|Director|Specialist|Lead|Coordinator|Consultant|Associate|Intern|Officer|Executive|President|Head|VP|Chief))',
        re.IGNORECASE
    )

    date_range_pattern = re.compile(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s*\d{4}|(?:\d{4}))\s*(?:-|–|to)\s*(Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s*\d{4}|\d{4})',
        re.IGNORECASE
    )

    current_job = None
    current_bullets = []

    for line in lines:
        line_stripped = line.strip()

        # Check for date range
        date_match = date_range_pattern.search(line_stripped)

        # Check for title
        title_match = title_pattern.search(line_stripped)

        if (title_match or date_match) and len(line_stripped) > 10:
            # Save previous job
            if current_job:
                current_job.bullets = current_bullets
                jobs.append(current_job)
                current_bullets = []

            # Extract job info
            title = title_match.group(1).strip() if title_match else "Unknown"

            start_date = None
            end_date = None
            is_current = False

            if date_match:
                start_date = parse_date(date_match.group(1))
                end_str = date_match.group(2)
                if 'present' in end_str.lower() or 'current' in end_str.lower():
                    end_date = None
                    is_current = True
                else:
                    end_date = parse_date(end_str)

            # Calculate duration
            duration = 0
            if start_date:
                end = end_date or date.today()
                duration = (end.year - start_date.year) * 12 + (end.month - start_date.month)

            current_job = JobEntry(
                title=title,
                company="",  # Would need more parsing
                start_date=start_date,
                end_date=end_date,
                duration_months=duration,
                hierarchy_level=get_title_hierarchy_level(title),
                is_current=is_current
            )

        elif current_job and (line_stripped.startswith(('•', '-', '*', '◦', '▪')) or
                              (len(line_stripped) > 20 and line_stripped[0].isupper())):
            # This looks like a bullet point
            bullet = re.sub(r'^[•\-\*\◦\▪]\s*', '', line_stripped)
            if len(bullet) > 15:
                current_bullets.append(bullet)

    # Don't forget the last job
    if current_job:
        current_job.bullets = current_bullets
        jobs.append(current_job)

    return jobs


def extract_skills_from_jd(text: str) -> List[str]:
    """Extract skill requirements from job description."""
    skills = []

    # Pattern matching for skills
    skill_patterns = [
        r'(?:experience\s+(?:with|in)|knowledge\s+of|proficiency\s+in|expertise\s+in)\s+([A-Za-z\s,/]+)',
        r'(?:skills?|requirements?|qualifications?):\s*([A-Za-z\s,/•\-]+)',
    ]

    for pattern in skill_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            # Split by common delimiters
            parts = re.split(r'[,;•\-\n]', m)
            for part in parts:
                part = part.strip()
                if 3 < len(part) < 50:
                    skills.append(part)

    # Also extract capitalized technical terms
    tech_terms = re.findall(r'\b([A-Z][a-z]*(?:\.[A-Za-z]+)?(?:\s+[A-Z][a-z]+)?)\b', text)
    for term in tech_terms:
        if 2 < len(term) < 30 and term not in ['The', 'This', 'You', 'Our', 'Your', 'We', 'They']:
            skills.append(term)

    return list(set(skills))[:30]


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def score_experience_alignment(
    resume_text: str,
    jd_text: str
) -> Tuple[float, ExperienceAnalysis]:
    """
    Score experience alignment using trapezoidal function.

    Scoring:
    - Under 50% requirement: Knockout (low score)
    - 50-100% requirement: Ramp up
    - 100-150% requirement: Sweet spot (100)
    - Over 150%: Decay (overqualified risk)
    """
    # Extract required years from JD
    required_years = extract_years_from_text(jd_text) or 5.0

    # Estimate candidate years from resume
    # Look for total experience mentions
    candidate_years = extract_years_from_text(resume_text)

    # If not found, estimate from job entries
    if not candidate_years:
        jobs = extract_jobs_from_text(resume_text)
        total_months = sum(j.duration_months for j in jobs if j.duration_months > 0)
        candidate_years = total_months / 12.0

    if candidate_years is None or candidate_years == 0:
        # Default estimate based on content
        candidate_years = 3.0  # Conservative default

    # Trapezoidal scoring
    C = candidate_years
    R = max(required_years, 1)  # Prevent division by zero

    if C < 0.5 * R:
        score = max(10, (C / (0.5 * R)) * 50)
        assessment = f"Below minimum: {C:.1f} years < {0.5*R:.1f} years minimum"
    elif C < R:
        score = 50 + ((C - 0.5 * R) / (0.5 * R)) * 50
        assessment = f"Approaching target: {C:.1f} years vs {R:.1f} required"
    elif C <= 1.5 * R:
        score = 100
        assessment = f"Sweet spot: {C:.1f} years in ideal range ({R:.1f}-{1.5*R:.1f})"
    else:
        # Overqualified decay
        decay = 10 * (C - 1.5 * R)
        score = max(70, 100 - decay)
        assessment = f"Overqualified: {C:.1f} years > {1.5*R:.1f} years (flight risk)"

    analysis = ExperienceAnalysis(
        total_years=candidate_years,
        required_years=required_years,
        alignment_score=score,
        assessment=assessment
    )

    return score, analysis


def score_skills_coverage(
    resume_text: str,
    jd_text: str
) -> Tuple[float, SkillsCoverage]:
    """Score skills coverage - how well resume covers JD requirements."""
    jd_skills = extract_skills_from_jd(jd_text)

    if not jd_skills:
        return 80.0, SkillsCoverage(80, [], [], 0.8)  # Default if no skills found

    resume_lower = resume_text.lower()
    bullets = extract_bullets_from_text(resume_text)
    bullets_text = ' '.join(bullets).lower()

    matched = []
    missing = []
    total_score = 0

    for skill in jd_skills:
        skill_lower = skill.lower()
        skill_words = skill_lower.split()

        # Check for skill presence with context weighting
        found = False
        weight = 0

        # Check in bullet points (higher weight)
        if any(word in bullets_text for word in skill_words if len(word) > 2):
            weight = 2.0
            found = True
            # Extra weight if appears multiple times
            count = sum(1 for b in bullets if any(w in b.lower() for w in skill_words))
            if count >= 3:
                weight = 3.0
        # Check in general resume text
        elif any(word in resume_lower for word in skill_words if len(word) > 2):
            weight = 1.0
            found = True

        if found:
            matched.append(skill)
            total_score += weight
        else:
            missing.append(skill)

    max_score = len(jd_skills) * 3.0  # Max weight per skill
    coverage_rate = len(matched) / len(jd_skills) if jd_skills else 0
    score = (total_score / max_score) * 100 if max_score > 0 else 50

    analysis = SkillsCoverage(
        score=min(100, score),
        matched=matched,
        missing=missing,
        coverage_rate=coverage_rate
    )

    return min(100, score), analysis


def score_career_trajectory(resume_text: str) -> Tuple[float, TrajectoryAnalysis]:
    """
    Score career trajectory using linear regression on title hierarchy.
    """
    jobs = extract_jobs_from_text(resume_text)

    if len(jobs) < 2:
        return 75, TrajectoryAnalysis(75, 'stable', 0, "Insufficient data for trajectory analysis")

    # Sort by start date
    sorted_jobs = sorted(
        [j for j in jobs if j.start_date],
        key=lambda x: x.start_date
    )

    if len(sorted_jobs) < 2:
        return 75, TrajectoryAnalysis(75, 'stable', 0, "Insufficient dated positions")

    # Create time series
    x_values = []
    y_values = []
    base_date = sorted_jobs[0].start_date

    for job in sorted_jobs:
        months = (job.start_date.year - base_date.year) * 12 + (job.start_date.month - base_date.month)
        x_values.append(months)
        y_values.append(job.hierarchy_level)

    # Simple linear regression
    n = len(x_values)
    if n < 2:
        return 75, TrajectoryAnalysis(75, 'stable', 0, "Not enough data points")

    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x * x for x in x_values)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        slope = 0
    else:
        slope = (n * sum_xy - sum_x * sum_y) / denominator

    annual_slope = slope * 12

    # Convert slope to score
    if annual_slope > 0.3:
        score = 100
        direction = 'ascending'
        narrative = f"Fast Track: Rapid progression ({annual_slope:.2f} levels/year)"
    elif annual_slope > 0.1:
        score = 90
        direction = 'ascending'
        narrative = f"Strong Growth: Consistent upward trajectory ({annual_slope:.2f} levels/year)"
    elif annual_slope >= 0:
        score = 80
        direction = 'stable'
        narrative = f"Stable: Steady career ({annual_slope:.2f} levels/year)"
    elif annual_slope > -0.1:
        score = 60
        direction = 'stable'
        narrative = f"Stagnant: Limited progression ({annual_slope:.2f} levels/year)"
    else:
        score = 40
        direction = 'descending'
        narrative = f"Concerning: Apparent regression ({annual_slope:.2f} levels/year)"

    return score, TrajectoryAnalysis(score, direction, annual_slope, narrative)


def score_impact_density(resume_text: str) -> Tuple[float, ImpactAnalysis]:
    """
    Score based on density of impact indicators.

    Looks for:
    - Metrics (%, $, numbers)
    - Strong action verbs
    - Quantified achievements
    """
    bullets = extract_bullets_from_text(resume_text)

    if not bullets:
        return 50, ImpactAnalysis(50, 0, 0, 0, 0, 0)

    metrics_count = 0
    strong_verbs_count = 0
    weak_verbs_count = 0

    # Metric patterns
    metric_patterns = [
        r'(\d+)%',  # Percentages
        r'\$[\d,.]+[MBK]?',  # Dollar amounts
        r'\b\d{1,3}(?:,\d{3})+\b',  # Large numbers
        r'\b\d+\s*(?:x|times)\b',  # Multipliers
        r'\b(?:doubled|tripled|quadrupled)\b',  # Word multipliers
    ]

    # Flatten strong verbs
    all_strong_verbs = []
    for verb_list in STRONG_ACTION_VERBS.values():
        all_strong_verbs.extend(verb_list)

    for bullet in bullets:
        bullet_lower = bullet.lower()

        # Check for metrics
        has_metric = any(re.search(p, bullet, re.IGNORECASE) for p in metric_patterns)
        if has_metric:
            metrics_count += 1

        # Check for strong verbs at start
        first_word = bullet.split()[0].lower().rstrip('ed').rstrip('ing') if bullet.split() else ''
        if any(verb in bullet_lower[:50] for verb in all_strong_verbs):
            strong_verbs_count += 1

        # Check for weak verbs
        if any(weak in bullet_lower for weak in WEAK_VERBS):
            weak_verbs_count += 1

    total_bullets = len(bullets)
    metrics_density = metrics_count / total_bullets if total_bullets > 0 else 0
    strong_ratio = strong_verbs_count / total_bullets if total_bullets > 0 else 0
    weak_ratio = weak_verbs_count / total_bullets if total_bullets > 0 else 0

    # Calculate verb power index (0-100)
    verb_power_index = min(100, strong_ratio * 150 - weak_ratio * 50)

    # Combined score
    density = (metrics_count + strong_verbs_count) / total_bullets if total_bullets > 0 else 0
    base_score = min(70, density * 175)
    verb_contribution = verb_power_index * 0.15

    # Bonus for high metrics density
    metrics_bonus = min(20, metrics_density * 50)

    score = base_score + verb_contribution + metrics_bonus

    # Penalty for weak verbs
    if weak_ratio > 0.3:
        score -= 10

    # Penalty if metrics density is too low
    if metrics_density < 0.3:
        penalty = max(1, (0.3 - metrics_density) * 25)
        score -= penalty

    analysis = ImpactAnalysis(
        score=max(0, min(100, score)),
        metrics_count=metrics_count,
        strong_verbs_count=strong_verbs_count,
        weak_verbs_count=weak_verbs_count,
        metrics_density=round(metrics_density * 100, 1),
        verb_power_index=round(verb_power_index, 1)
    )

    return max(0, min(100, score)), analysis


def score_title_match(
    resume_text: str,
    jd_text: str
) -> Tuple[float, TitleMatchAnalysis]:
    """Score role title similarity between resume and JD."""
    # Extract target level from JD
    jd_lower = jd_text.lower()
    target_level = 3  # Default mid

    for title, level in TITLE_HIERARCHY.items():
        if title in jd_lower:
            target_level = max(target_level, level)

    # Get candidate's most recent/highest level
    jobs = extract_jobs_from_text(resume_text)
    if not jobs:
        return 70, TitleMatchAnalysis(70, 3, target_level, "Unable to determine candidate level")

    # Use most recent job's level, or highest if current
    resume_level = max(j.hierarchy_level for j in jobs[:3]) if jobs else 3

    # Score based on level difference
    level_diff = abs(target_level - resume_level)

    if level_diff == 0:
        score = 100
        assessment = "Perfect match: Candidate level matches target role"
    elif level_diff == 1:
        score = 90
        assessment = "Close match: Candidate is one level off"
    elif resume_level > target_level:
        score = 80 - (level_diff - 1) * 10
        assessment = f"Overqualified: Candidate is {level_diff} levels above target"
    else:
        score = 70 - (level_diff - 1) * 15
        assessment = f"Stretch role: Candidate is {level_diff} levels below target"

    return max(40, min(100, score)), TitleMatchAnalysis(
        score=max(40, min(100, score)),
        resume_level=resume_level,
        target_level=target_level,
        assessment=assessment
    )


def calculate_penalties(
    resume_text: str,
    jd_text: str
) -> Tuple[float, Dict[str, float], List[str]]:
    """Calculate risk penalties for job hopping, gaps, etc."""
    penalties = {}
    concerns = []
    total_penalty = 0

    jobs = extract_jobs_from_text(resume_text)

    # Job hopping check
    if len(jobs) >= 3:
        tenures = [j.duration_months for j in jobs if j.duration_months > 0]
        if tenures:
            avg_tenure = sum(tenures) / len(tenures)

            # Check for contract/temp roles
            contract_keywords = {'contract', 'temporary', 'interim', 'consultant', 'freelance'}
            contract_count = sum(1 for j in jobs if any(kw in j.title.lower() for kw in contract_keywords))
            penalty_mult = 0.5 if contract_count >= len(jobs) * 0.4 else 1.0

            if avg_tenure < 12:
                penalties['job_hopping'] = round(15 * penalty_mult)
                concerns.append(f"High turnover: Avg tenure {avg_tenure:.0f} months")
            elif avg_tenure < 18:
                penalties['job_hopping'] = round(8 * penalty_mult)
                concerns.append(f"Moderate turnover: Avg tenure {avg_tenure:.0f} months")

    # Gap detection
    sorted_jobs = sorted([j for j in jobs if j.start_date], key=lambda x: x.start_date)

    for i in range(len(sorted_jobs) - 1):
        current_end = sorted_jobs[i].end_date or date.today()
        next_start = sorted_jobs[i + 1].start_date

        if next_start and current_end:
            gap_months = (next_start.year - current_end.year) * 12 + (next_start.month - current_end.month)
            if gap_months > 6:
                # Check for explanation
                resume_lower = resume_text.lower()
                has_explanation = any(exp in resume_lower for exp in GAP_EXPLANATIONS)

                if not has_explanation:
                    if gap_months > 24:
                        penalties['unexplained_gap'] = 15
                        concerns.append(f"Major unexplained gap: {gap_months} months")
                    elif gap_months > 12:
                        penalties['unexplained_gap'] = 10
                        concerns.append(f"Unexplained gap: {gap_months} months")
                    break

    total_penalty = sum(penalties.values())
    return total_penalty, penalties, concerns


def detect_ai_writing(resume_text: str) -> Tuple[float, List[str]]:
    """Detect potential AI-generated content via cliché verbs and uniformity."""
    bullets = extract_bullets_from_text(resume_text)
    warnings = []

    if not bullets or len(bullets) < 3:
        return 0, []

    # Check for AI cliché verbs
    cliche_count = 0
    for bullet in bullets:
        first_word = bullet.split()[0].lower().rstrip('.,;:') if bullet.split() else ''
        if first_word in AI_CLICHE_VERBS:
            cliche_count += 1

    cliche_ratio = cliche_count / len(bullets)
    if cliche_ratio > 0.3:
        warnings.append(f"High AI cliché verb usage: {cliche_count}/{len(bullets)} bullets")

    # Check sentence length uniformity (AI tends to be uniform)
    word_counts = [len(b.split()) for b in bullets]
    if len(word_counts) > 3:
        mean_wc = sum(word_counts) / len(word_counts)
        std_dev = (sum((w - mean_wc) ** 2 for w in word_counts) / len(word_counts)) ** 0.5
        cv = std_dev / mean_wc if mean_wc else 0

        if cv < 0.15:
            warnings.append("Suspiciously uniform sentence lengths (potential AI writing)")

    penalty = min(10, cliche_ratio * 20)
    return penalty, warnings


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def calculate_hr_score(
    resume_text: str,
    jd_text: str
) -> HRScoreResult:
    """
    Calculate comprehensive HR score for resume vs job description.

    Args:
        resume_text: Resume content as text
        jd_text: Job description content as text

    Returns:
        HRScoreResult with comprehensive scoring and feedback
    """
    strengths = []
    concerns = []

    # Determine seniority for weight selection
    seniority = determine_seniority_level(jd_text)
    weights = WEIGHT_PROFILES.get(seniority, WEIGHT_PROFILES['mid'])

    # 1. Experience Score
    exp_score, exp_analysis = score_experience_alignment(resume_text, jd_text)
    if exp_score >= 80:
        strengths.append(exp_analysis.assessment)
    elif exp_score < 60:
        concerns.append(exp_analysis.assessment)

    # 2. Skills Score
    skills_score, skills_analysis = score_skills_coverage(resume_text, jd_text)
    if skills_analysis.matched:
        strengths.append(f"Skills Match: {len(skills_analysis.matched)} required skills demonstrated")
    if skills_analysis.missing:
        concerns.append(f"Missing Skills: {', '.join(skills_analysis.missing[:3])}")

    # 3. Trajectory Score
    traj_score, traj_analysis = score_career_trajectory(resume_text)
    if traj_score >= 90:
        strengths.append(traj_analysis.narrative)
    elif traj_score < 60:
        concerns.append(traj_analysis.narrative)

    # 4. Impact Score
    impact_score, impact_analysis = score_impact_density(resume_text)
    if impact_analysis.metrics_density >= 30:
        strengths.append(f"High Impact: {impact_analysis.metrics_density:.0f}% of achievements quantified")
    elif impact_analysis.metrics_density < 15:
        concerns.append(f"Low Quantification: Only {impact_analysis.metrics_density:.0f}% metrics")

    # 5. Title Match Score
    title_score, title_analysis = score_title_match(resume_text, jd_text)
    if title_score >= 90:
        strengths.append(title_analysis.assessment)
    elif title_score < 70:
        concerns.append(title_analysis.assessment)

    # Calculate raw score
    raw_score = (
        exp_score * weights['experience'] +
        skills_score * weights['skills'] +
        traj_score * weights['trajectory'] +
        impact_score * weights['impact'] +
        title_score * weights['title_match']
    )

    # Apply penalties
    penalty_total, penalties, penalty_concerns = calculate_penalties(resume_text, jd_text)
    concerns.extend(penalty_concerns)

    # AI writing detection
    ai_penalty, ai_warnings = detect_ai_writing(resume_text)
    if ai_warnings:
        penalties['ai_writing'] = ai_penalty
        concerns.extend(ai_warnings)
        penalty_total += ai_penalty

    final_score = max(0, min(100, raw_score - penalty_total))

    # Determine recommendation
    if final_score >= 80:
        recommendation = "STRONG INTERVIEW"
        rating_label = "Strong Candidate"
    elif final_score >= 65:
        recommendation = "INTERVIEW"
        rating_label = "Competitive"
    elif final_score >= 50:
        recommendation = "MAYBE"
        rating_label = "Marginal - Screening Recommended"
    else:
        recommendation = "PASS"
        rating_label = "Weak Match"

    # Generate interview questions
    questions = []
    if 'unexplained_gap' in penalties:
        questions.append("Can you walk me through the gap in your employment history?")
    if 'job_hopping' in penalties:
        questions.append("What's driving your interest in a longer-term opportunity?")
    if impact_score < 60:
        questions.append("Can you quantify the impact of your work at your most recent role?")
    if traj_score < 70:
        questions.append("Where do you see your career heading in the next 3-5 years?")
    if not questions:
        questions.append("What attracted you to this specific opportunity?")

    # Calculate confidence
    jobs = extract_jobs_from_text(resume_text)
    bullets = extract_bullets_from_text(resume_text)
    data_completeness = min(100, len(jobs) * 15 + len(bullets) * 2)
    confidence = 'High' if data_completeness > 70 else 'Medium' if data_completeness > 40 else 'Low'

    # Build breakdown
    breakdown = {
        'experience': {
            'score': round(exp_score, 1),
            'total_years': exp_analysis.total_years,
            'required_years': exp_analysis.required_years,
            'assessment': exp_analysis.assessment,
        },
        'skills': {
            'score': round(skills_score, 1),
            'matched': skills_analysis.matched[:10],
            'missing': skills_analysis.missing[:10],
            'coverage_rate': round(skills_analysis.coverage_rate * 100, 1),
        },
        'trajectory': {
            'score': round(traj_score, 1),
            'direction': traj_analysis.direction,
            'annual_slope': round(traj_analysis.annual_slope, 3),
            'narrative': traj_analysis.narrative,
        },
        'impact': {
            'score': round(impact_score, 1),
            'metrics_count': impact_analysis.metrics_count,
            'strong_verbs': impact_analysis.strong_verbs_count,
            'weak_verbs': impact_analysis.weak_verbs_count,
            'metrics_density': impact_analysis.metrics_density,
        },
        'title_match': {
            'score': round(title_score, 1),
            'resume_level': title_analysis.resume_level,
            'target_level': title_analysis.target_level,
            'assessment': title_analysis.assessment,
        },
        'seniority_detected': seniority,
    }

    return HRScoreResult(
        overall_score=final_score,
        recommendation=recommendation,
        rating_label=rating_label,
        confidence=f"{confidence} ({data_completeness:.0f}%)",
        experience_score=exp_score,
        skills_score=skills_score,
        trajectory_score=traj_score,
        impact_score=impact_score,
        title_match_score=title_score,
        strengths=strengths[:5],
        concerns=concerns[:5],
        suggested_questions=questions[:4],
        penalties_applied=penalties,
        weights_used=weights,
        breakdown=breakdown,
    )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def score_resume_hr(
    resume_text: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Score a resume from an HR perspective.

    Convenience function that returns a dictionary.

    Args:
        resume_text: Resume content
        job_description: Job description content

    Returns:
        Dictionary with HR scoring results
    """
    result = calculate_hr_score(resume_text, job_description)
    return result.to_dict()

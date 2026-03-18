"""
ATS (Applicant Tracking System) Resume Scorer

Rule-based ATS scoring that evaluates resume-job description fit through:
- Keyword/phrase matching against job description
- Section detection (experience, skills, education, summary)
- Formatting checks (bullet points, dates, structure)
- Keyword density assessment

Ported from Resume-Builder, adapted for WinningCV.
No SBERT/semantic similarity - pure rule-based scoring.
"""

import re
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
    'shall', 'can', 'need', 'dare', 'ought', 'used', 'it', 'its', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they', 'what', 'which', 'who',
    'whom', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there',
    'then', 'once', 'if', 'unless', 'until', 'while', 'during', 'before', 'after',
    'above', 'below', 'between', 'into', 'through', 'about', 'against', 'over',
    'under', 'again', 'further', 'any', 'our', 'your', 'their', 'his', 'her', 'my',
    'etc', 'eg', 'ie', 'via', 'per', 'vs', 'including', 'within', 'across', 'along',
    'among', 'around', 'behind', 'beyond', 'like', 'near', 'since', 'upon', 'based'
}

# JD boilerplate words - common in job descriptions but NOT meaningful skills
JD_BOILERPLATE_WORDS = {
    'position', 'job', 'role', 'opportunity', 'candidate', 'applicant',
    'requirement', 'qualification', 'responsibility', 'duty', 'duties',
    'company', 'organization', 'employer', 'employee', 'team', 'department',
    'salary', 'compensation', 'benefits', 'package', 'competitive',
    'equal', 'eoe', 'diversity', 'inclusion',
    'preferred', 'required', 'desired', 'minimum', 'maximum',
    'experience', 'year', 'years', 'month', 'months',
    'able', 'ability', 'capable', 'proficient', 'excellent',
    'strong', 'proven', 'demonstrated', 'successful', 'effective',
    'work', 'working', 'environment', 'office', 'remote', 'hybrid',
    'full', 'time', 'part', 'contract', 'permanent', 'temporary',
    'apply', 'submit', 'resume', 'cover', 'letter', 'application',
    'please', 'note', 'must', 'shall', 'ensure', 'provide',
    'support', 'assist', 'help', 'maintain', 'manage', 'develop',
    'report', 'review', 'prepare', 'coordinate', 'oversee',
    'retail', 'location', 'travel', 'schedule', 'shift',
    'ideal', 'looking', 'seeking', 'join', 'growing',
    'dynamic', 'innovative', 'exciting', 'passionate', 'motivated',
    'self', 'starter', 'driven', 'oriented', 'focused',
    'detail', 'details', 'fast', 'paced', 'multi', 'task',
    'independently', 'level', 'senior', 'junior', 'entry', 'mid',
    'include', 'includes', 'including', 'involve', 'involves',
    'perform', 'performs', 'responsible', 'various', 'multiple',
}

ALL_STOP_WORDS = STOP_WORDS | JD_BOILERPLATE_WORDS

# Common acronyms and their expansions
ACRONYMS = {
    'ai': 'artificial intelligence',
    'ml': 'machine learning',
    'nlp': 'natural language processing',
    'aws': 'amazon web services',
    'gcp': 'google cloud platform',
    'ci': 'continuous integration',
    'cd': 'continuous deployment',
    'api': 'application programming interface',
    'sql': 'structured query language',
    'html': 'hypertext markup language',
    'css': 'cascading style sheets',
    'js': 'javascript',
    'ts': 'typescript',
    'ui': 'user interface',
    'ux': 'user experience',
    'qa': 'quality assurance',
    'pm': 'project manager',
    'hr': 'human resources',
    'kpi': 'key performance indicator',
    'roi': 'return on investment',
    'b2b': 'business to business',
    'b2c': 'business to consumer',
    'saas': 'software as a service',
    'crm': 'customer relationship management',
    'erp': 'enterprise resource planning',
    'devops': 'development operations',
    'seo': 'search engine optimization',
    'ppc': 'pay per click',
}

# Domain detection patterns
DOMAIN_PATTERNS = {
    'technology': {
        'keywords': ['software', 'engineer', 'developer', 'python', 'java', 'javascript',
                    'cloud', 'aws', 'azure', 'kubernetes', 'docker', 'api', 'microservices',
                    'agile', 'scrum', 'devops', 'machine learning', 'data science',
                    'frontend', 'backend', 'fullstack', 'react', 'node', 'database'],
    },
    'finance': {
        'keywords': ['investment', 'banking', 'private equity', 'hedge fund', 'trading',
                    'valuation', 'financial modeling', 'portfolio', 'derivatives',
                    'equity', 'fixed income', 'risk management', 'compliance', 'audit'],
    },
    'marketing': {
        'keywords': ['marketing', 'brand', 'digital marketing', 'content', 'social media',
                    'campaign', 'analytics', 'seo', 'ppc', 'conversion', 'engagement',
                    'growth', 'acquisition', 'retention', 'funnel'],
    },
    'healthcare': {
        'keywords': ['healthcare', 'medical', 'clinical', 'patient', 'hospital',
                    'nursing', 'physician', 'health system', 'hipaa', 'ehr', 'emr',
                    'pharmaceutical', 'biotech', 'fda', 'clinical trial'],
    },
    'consulting': {
        'keywords': ['consulting', 'strategy', 'advisory', 'client engagement',
                    'stakeholder', 'transformation', 'change management',
                    'due diligence', 'market analysis', 'implementation'],
    },
}

# Resume section patterns
SECTION_PATTERNS = {
    'experience': r'\b(experience|employment|work\s*history|professional\s*background|career)\b',
    'education': r'\b(education|academic|degree|university|college|school|certification|certifications)\b',
    'skills': r'\b(skills|technical\s*skills|core\s*competencies|competencies|expertise|technologies)\b',
    'summary': r'\b(summary|profile|objective|about|overview|introduction)\b',
    'projects': r'\b(projects|portfolio|achievements|accomplishments)\b',
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SectionAnalysis:
    """Analysis of resume sections."""
    sections_found: List[str] = field(default_factory=list)
    sections_missing: List[str] = field(default_factory=list)
    section_order_score: float = 0.0
    has_clear_structure: bool = False


@dataclass
class FormattingAnalysis:
    """Analysis of resume formatting."""
    has_bullet_points: bool = False
    bullet_count: int = 0
    has_dates: bool = False
    date_count: int = 0
    has_consistent_formatting: bool = False
    line_length_variance: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class KeywordAnalysis:
    """Analysis of keyword matching."""
    matched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    match_rate: float = 0.0
    density_score: float = 0.0
    density_assessment: str = "Unknown"


@dataclass
class ATSScoreResult:
    """Complete ATS scoring result."""
    total_score: float
    keyword_score: float
    phrase_score: float
    section_score: float
    formatting_score: float
    density_score: float

    matched_keywords: List[str]
    missing_keywords: List[str]
    matched_phrases: List[str]
    missing_phrases: List[str]

    sections_found: List[str]
    sections_missing: List[str]
    formatting_warnings: List[str]

    domain_detected: str
    likelihood_rating: str

    breakdown: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_score': round(self.total_score, 1),
            'keyword_score': round(self.keyword_score, 1),
            'phrase_score': round(self.phrase_score, 1),
            'section_score': round(self.section_score, 1),
            'formatting_score': round(self.formatting_score, 1),
            'density_score': round(self.density_score, 1),
            'matched_keywords': self.matched_keywords[:15],
            'missing_keywords': self.missing_keywords[:15],
            'matched_phrases': self.matched_phrases,
            'missing_phrases': self.missing_phrases,
            'sections_found': self.sections_found,
            'sections_missing': self.sections_missing,
            'formatting_warnings': self.formatting_warnings,
            'domain_detected': self.domain_detected,
            'likelihood_rating': self.likelihood_rating,
            'breakdown': self.breakdown,
        }


# =============================================================================
# TEXT PROCESSING
# =============================================================================

def clean_text(text: str) -> str:
    """Clean and normalize text for matching."""
    text = text.lower()
    text = re.sub(r'[^\w\s\-/]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def lemmatize_simple(word: str) -> str:
    """Simple suffix-stripping lemmatization."""
    word = word.lower()
    suffixes = ['ing', 'ed', 'er', 'est', 'ly', 'tion', 'ment', 's', 'es']
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[:-len(suffix)]
    return word


def expand_acronyms(text: str) -> str:
    """Expand known acronyms in text."""
    text_lower = text.lower()
    additions = []

    for acronym, expansion in ACRONYMS.items():
        pattern = r'\b' + re.escape(acronym) + r'\b'
        if re.search(pattern, text_lower, re.IGNORECASE):
            additions.append(expansion)

    if additions:
        text = text + ' ' + ' '.join(additions)

    return text


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract meaningful keywords from text."""
    text = expand_acronyms(text)
    cleaned = clean_text(text)
    words = cleaned.split()

    # Filter stop words and short words
    keywords = []
    seen = set()

    for w in words:
        if w not in ALL_STOP_WORDS and len(w) >= min_length:
            # Add original and lemmatized form
            if w not in seen:
                keywords.append(w)
                seen.add(w)
            lemma = lemmatize_simple(w)
            if lemma != w and lemma not in seen:
                keywords.append(lemma)
                seen.add(lemma)

    return keywords


def extract_phrases(text: str, min_words: int = 2, max_words: int = 4) -> List[str]:
    """Extract multi-word phrases from text."""
    cleaned = clean_text(text)
    words = cleaned.split()
    phrases = []

    for n in range(min_words, min(max_words + 1, len(words) + 1)):
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            # Skip if mostly stop words
            phrase_words = phrase.split()
            non_stop = [w for w in phrase_words if w not in ALL_STOP_WORDS]
            if len(non_stop) >= n - 1:  # At least n-1 non-stop words
                phrases.append(phrase)

    return phrases


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def detect_domain(text: str) -> Tuple[str, float, Dict[str, float]]:
    """Auto-detect the industry domain from text."""
    text_lower = text.lower()
    domain_scores = {}

    for domain, config in DOMAIN_PATTERNS.items():
        score = 0
        for keyword in config['keywords']:
            if keyword in text_lower:
                score += 1
        domain_scores[domain] = round((score / len(config['keywords'])) * 100, 1)

    if domain_scores:
        primary_domain = max(domain_scores, key=domain_scores.get)
        confidence = domain_scores[primary_domain]
    else:
        primary_domain = 'general'
        confidence = 0

    return primary_domain, confidence, domain_scores


def calculate_keyword_match(
    resume_text: str,
    jd_text: str
) -> Tuple[float, List[str], List[str]]:
    """Calculate keyword match score between resume and JD."""
    # Extract keywords from JD
    jd_keywords = extract_keywords(jd_text)

    # Get frequency count - weight by importance
    jd_cleaned = clean_text(jd_text)
    word_counts = Counter(jd_cleaned.split())

    # Filter to meaningful keywords that appear multiple times or are longer
    important_jd_keywords = []
    for kw in jd_keywords:
        count = word_counts.get(kw, 0)
        if count >= 2 or len(kw) >= 6:
            important_jd_keywords.append(kw)

    # Limit to top keywords
    important_jd_keywords = list(set(important_jd_keywords))[:50]

    if not important_jd_keywords:
        return 100.0, [], []

    # Check matches in resume
    resume_cleaned = clean_text(expand_acronyms(resume_text))
    resume_tokens = set(resume_cleaned.split())

    # Also add lemmatized forms
    resume_lemmas = set()
    for token in resume_tokens:
        resume_lemmas.add(token)
        resume_lemmas.add(lemmatize_simple(token))

    matched = []
    missing = []

    for kw in important_jd_keywords:
        kw_lemma = lemmatize_simple(kw)
        if kw in resume_lemmas or kw_lemma in resume_lemmas:
            matched.append(kw)
        else:
            missing.append(kw)

    match_rate = len(matched) / len(important_jd_keywords) * 100 if important_jd_keywords else 0

    return match_rate, matched, missing


def calculate_phrase_match(
    resume_text: str,
    jd_text: str
) -> Tuple[float, List[str], List[str]]:
    """Calculate phrase match score (multi-word terms)."""
    # Extract phrases from JD
    jd_phrases = extract_phrases(jd_text, min_words=2, max_words=4)

    # Count phrase frequency to find important ones
    jd_cleaned = clean_text(jd_text)
    important_phrases = []

    for phrase in set(jd_phrases):
        # Only keep phrases that appear as coherent unit
        if phrase in jd_cleaned and len(phrase.split()) >= 2:
            # Check it's not mostly stop words
            words = phrase.split()
            non_stop = [w for w in words if w not in ALL_STOP_WORDS and len(w) > 2]
            if len(non_stop) >= 1:
                important_phrases.append(phrase)

    # Limit to reasonable number
    important_phrases = important_phrases[:30]

    if not important_phrases:
        return 100.0, [], []

    resume_cleaned = clean_text(expand_acronyms(resume_text))

    matched = []
    missing = []

    for phrase in important_phrases:
        if phrase in resume_cleaned:
            matched.append(phrase)
        else:
            missing.append(phrase)

    match_rate = len(matched) / len(important_phrases) * 100 if important_phrases else 0

    return match_rate, matched, missing


def analyze_sections(resume_text: str) -> SectionAnalysis:
    """Analyze resume section structure."""
    resume_lower = resume_text.lower()
    analysis = SectionAnalysis()

    expected_sections = ['experience', 'education', 'skills']
    optional_sections = ['summary', 'projects']

    # Check for each section
    for section, pattern in SECTION_PATTERNS.items():
        if re.search(pattern, resume_lower, re.IGNORECASE):
            analysis.sections_found.append(section)
        elif section in expected_sections:
            analysis.sections_missing.append(section)

    # Score section structure
    found_expected = len([s for s in expected_sections if s in analysis.sections_found])
    analysis.section_order_score = (found_expected / len(expected_sections)) * 100

    # Check if has clear structure (headers, consistent formatting)
    header_patterns = [
        r'^[A-Z][A-Z\s]+$',  # ALL CAPS headers
        r'^#{1,3}\s',  # Markdown headers
        r'^\*\*[^*]+\*\*$',  # Bold text
    ]

    lines = resume_text.split('\n')
    header_count = 0
    for line in lines:
        line = line.strip()
        for pattern in header_patterns:
            if re.match(pattern, line):
                header_count += 1
                break

    analysis.has_clear_structure = header_count >= 3

    return analysis


def analyze_formatting(resume_text: str) -> FormattingAnalysis:
    """Analyze resume formatting quality."""
    analysis = FormattingAnalysis()
    lines = resume_text.split('\n')

    # Check for bullet points
    bullet_patterns = [r'^\s*[•\-\*\◦\▪]', r'^\s*\d+\.']
    bullet_lines = []
    for line in lines:
        for pattern in bullet_patterns:
            if re.match(pattern, line.strip()):
                bullet_lines.append(line)
                break

    analysis.has_bullet_points = len(bullet_lines) > 0
    analysis.bullet_count = len(bullet_lines)

    # Check for dates
    date_patterns = [
        r'\b(19|20)\d{2}\b',  # Year
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s*(19|20)?\d{2,4}',
        r'\b\d{1,2}/\d{2,4}\b',
        r'\b(Present|Current)\b',
    ]

    date_count = 0
    for pattern in date_patterns:
        date_count += len(re.findall(pattern, resume_text, re.IGNORECASE))

    analysis.has_dates = date_count > 0
    analysis.date_count = date_count

    # Check line length consistency
    non_empty_lines = [len(line) for line in lines if line.strip()]
    if len(non_empty_lines) > 5:
        avg_length = sum(non_empty_lines) / len(non_empty_lines)
        variance = sum((l - avg_length) ** 2 for l in non_empty_lines) / len(non_empty_lines)
        analysis.line_length_variance = math.sqrt(variance)
        analysis.has_consistent_formatting = analysis.line_length_variance < 50

    # Generate warnings
    if not analysis.has_bullet_points:
        analysis.warnings.append("No bullet points detected - consider using bullets for achievements")
    elif analysis.bullet_count < 5:
        analysis.warnings.append("Few bullet points - resumes typically have 10-20 achievement bullets")

    if not analysis.has_dates:
        analysis.warnings.append("No dates detected - include employment dates for each role")
    elif analysis.date_count < 3:
        analysis.warnings.append("Limited date information - ensure each position has start/end dates")

    return analysis


def calculate_keyword_density(resume_text: str, jd_text: str) -> Tuple[float, str]:
    """Calculate keyword density and assess if it's appropriate."""
    jd_keywords = set(extract_keywords(jd_text)[:30])
    resume_cleaned = clean_text(resume_text)
    resume_words = resume_cleaned.split()
    total_words = len(resume_words)

    if total_words == 0:
        return 0, "Empty"

    # Count JD keyword occurrences in resume
    keyword_occurrences = 0
    for word in resume_words:
        lemma = lemmatize_simple(word)
        if word in jd_keywords or lemma in jd_keywords:
            keyword_occurrences += 1

    density = (keyword_occurrences / total_words) * 100

    # Assess density
    if density < 2:
        assessment = "Low"
        score = 40 + density * 15
    elif density <= 5:
        assessment = "Good"
        score = 80 + (density - 2) * 5
    elif density <= 8:
        assessment = "Adequate"
        score = 85 - (density - 5) * 3
    else:
        assessment = "High (potential stuffing)"
        score = max(40, 75 - (density - 8) * 5)

    return min(100, max(0, score)), assessment


def detect_keyword_stuffing(text: str) -> Tuple[bool, float, List[str]]:
    """Detect potential keyword stuffing."""
    cleaned = clean_text(text)
    words = cleaned.split()
    word_count = len(words)

    if word_count < 50:
        return False, 0, []

    # Calculate word frequencies
    word_freq = Counter(words)
    meaningful_words = {w: c for w, c in word_freq.items()
                       if w not in ALL_STOP_WORDS and len(w) > 2}

    if not meaningful_words:
        return False, 0, []

    # Calculate statistics
    frequencies = list(meaningful_words.values())
    mean_freq = sum(frequencies) / len(frequencies)
    variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
    std_dev = math.sqrt(variance) if variance > 0 else 1

    # Find outliers (>3 standard deviations)
    outliers = {w: c for w, c in meaningful_words.items()
               if c > mean_freq + 3 * std_dev}

    flags = []
    manipulation_score = 0

    if outliers:
        manipulation_score += 30
        flags.append(f"Excessive repetition of: {list(outliers.keys())[:5]}")

    # Check for consecutive repeated words
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            manipulation_score += 15
            flags.append(f"Triple repetition found: '{words[i]}'")
            break

    manipulation_score = min(100, manipulation_score)
    is_stuffed = manipulation_score > 40

    return is_stuffed, manipulation_score, flags


def get_likelihood_rating(score: float) -> str:
    """Convert score to likelihood rating."""
    if score >= 80:
        return "Excellent - Top Candidate"
    elif score >= 65:
        return "Good - Strong Match"
    elif score >= 50:
        return "Fair - Competitive"
    elif score >= 35:
        return "Low - Below Average"
    else:
        return "Poor - Unlikely Match"


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def calculate_ats_score(
    resume_text: str,
    jd_text: str
) -> ATSScoreResult:
    """
    Calculate comprehensive ATS score for resume vs job description.

    Args:
        resume_text: Resume content as text
        jd_text: Job description content as text

    Returns:
        ATSScoreResult with comprehensive scoring and breakdown
    """
    # Domain detection
    domain, domain_confidence, domain_scores = detect_domain(jd_text)

    # Keyword matching (30% weight)
    keyword_score, matched_kw, missing_kw = calculate_keyword_match(resume_text, jd_text)

    # Phrase matching (25% weight)
    phrase_score, matched_phrases, missing_phrases = calculate_phrase_match(resume_text, jd_text)

    # Section analysis (15% weight)
    sections = analyze_sections(resume_text)
    section_score = sections.section_order_score
    if sections.has_clear_structure:
        section_score = min(100, section_score + 20)

    # Formatting analysis (15% weight)
    formatting = analyze_formatting(resume_text)
    formatting_score = 50  # Base score
    if formatting.has_bullet_points:
        formatting_score += 20
    if formatting.has_dates:
        formatting_score += 20
    if formatting.has_consistent_formatting:
        formatting_score += 10
    formatting_score = min(100, formatting_score)

    # Keyword density (15% weight)
    density_score, density_assessment = calculate_keyword_density(resume_text, jd_text)

    # Check for stuffing (penalty)
    is_stuffed, stuffing_score, stuffing_flags = detect_keyword_stuffing(resume_text)

    # Calculate total score with weights
    total_score = (
        keyword_score * 0.30 +
        phrase_score * 0.25 +
        section_score * 0.15 +
        formatting_score * 0.15 +
        density_score * 0.15
    )

    # Apply stuffing penalty
    if is_stuffed:
        penalty = min(15, stuffing_score * 0.15)
        total_score -= penalty

    total_score = max(0, min(100, total_score))

    # Build breakdown
    breakdown = {
        'weights': {
            'keyword_match': 0.30,
            'phrase_match': 0.25,
            'sections': 0.15,
            'formatting': 0.15,
            'density': 0.15,
        },
        'keyword_analysis': {
            'total_jd_keywords': len(matched_kw) + len(missing_kw),
            'matched': len(matched_kw),
            'match_rate': round(keyword_score, 1),
        },
        'phrase_analysis': {
            'total_phrases': len(matched_phrases) + len(missing_phrases),
            'matched': len(matched_phrases),
            'match_rate': round(phrase_score, 1),
        },
        'section_analysis': {
            'found': sections.sections_found,
            'missing': sections.sections_missing,
            'has_clear_structure': sections.has_clear_structure,
        },
        'formatting_analysis': {
            'bullet_count': formatting.bullet_count,
            'has_dates': formatting.has_dates,
            'date_count': formatting.date_count,
        },
        'density_analysis': {
            'score': round(density_score, 1),
            'assessment': density_assessment,
        },
        'stuffing_detection': {
            'is_stuffed': is_stuffed,
            'score': round(stuffing_score, 1),
            'flags': stuffing_flags,
        },
        'domain': {
            'detected': domain,
            'confidence': domain_confidence,
            'all_scores': domain_scores,
        },
    }

    return ATSScoreResult(
        total_score=total_score,
        keyword_score=keyword_score,
        phrase_score=phrase_score,
        section_score=section_score,
        formatting_score=formatting_score,
        density_score=density_score,
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
        matched_phrases=matched_phrases,
        missing_phrases=missing_phrases,
        sections_found=sections.sections_found,
        sections_missing=sections.sections_missing,
        formatting_warnings=formatting.warnings,
        domain_detected=domain,
        likelihood_rating=get_likelihood_rating(total_score),
        breakdown=breakdown,
    )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def score_resume_ats(
    resume_text: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Score a resume against a job description for ATS compatibility.

    Convenience function that returns a dictionary.

    Args:
        resume_text: Resume content
        job_description: Job description content

    Returns:
        Dictionary with ATS scoring results
    """
    result = calculate_ats_score(resume_text, job_description)
    return result.to_dict()

"""
CV Knowledge Base Module.

Provides PostgreSQL-backed storage and retrieval of CV content for intelligent
CV generation using content from all previous CV versions.
"""
import asyncio
import hashlib
import logging
import re
from typing import Optional

import asyncpg

from config.settings_v2 import settings

logger = logging.getLogger(__name__)

# Section type patterns for extraction
SECTION_PATTERNS = {
    'summary': [
        r'(?i)^(?:professional\s+)?summary',
        r'(?i)^profile',
        r'(?i)^about\s+me',
        r'(?i)^executive\s+summary',
        r'(?i)^career\s+objective',
    ],
    'experience': [
        r'(?i)^(?:work\s+)?experience',
        r'(?i)^employment\s+history',
        r'(?i)^professional\s+experience',
        r'(?i)^career\s+history',
    ],
    'skills': [
        r'(?i)^(?:technical\s+)?skills',
        r'(?i)^competencies',
        r'(?i)^expertise',
        r'(?i)^core\s+skills',
    ],
    'education': [
        r'(?i)^education',
        r'(?i)^academic\s+background',
        r'(?i)^qualifications',
    ],
    'projects': [
        r'(?i)^projects',
        r'(?i)^key\s+projects',
        r'(?i)^notable\s+projects',
    ],
    'certifications': [
        r'(?i)^certifications?',
        r'(?i)^licenses?\s+(?:and|&)\s+certifications?',
        r'(?i)^professional\s+certifications?',
    ],
}


class CVKnowledgeBase:
    """
    Async PostgreSQL-backed CV Knowledge Base.

    Indexes CV content and provides intelligent retrieval for CV generation.
    """

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def get_pool(self) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    self._pool = await asyncpg.create_pool(
                        host=settings.postgres_host,
                        port=settings.postgres_port,
                        user=settings.postgres_user,
                        password=settings.postgres_password,
                        database=settings.postgres_db,
                        min_size=settings.postgres_pool_min,
                        max_size=settings.postgres_pool_max,
                    )
                    logger.info("PostgreSQL connection pool created")
        return self._pool

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def extract_sections(self, cv_content: str) -> list[dict]:
        """
        Parse CV text into sections.

        Args:
            cv_content: Raw CV text content

        Returns:
            List of section dicts with type, title, content, and position
        """
        sections = []
        lines = cv_content.split('\n')

        current_section = None
        current_content = []
        position = 0

        def save_current_section():
            nonlocal current_section, current_content, position
            if current_section and current_content:
                content = '\n'.join(current_content).strip()
                if content:
                    sections.append({
                        'section_type': current_section['type'],
                        'section_title': current_section['title'],
                        'content': content,
                        'position_order': position,
                    })
                    position += 1
            current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_content:
                    current_content.append('')
                continue

            # Check if this line is a section header
            section_type = None
            for stype, patterns in SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, stripped):
                        section_type = stype
                        break
                if section_type:
                    break

            if section_type:
                save_current_section()
                current_section = {
                    'type': section_type,
                    'title': stripped,
                }
            elif current_section:
                current_content.append(stripped)
            else:
                # Content before any section header - treat as summary
                if not current_section:
                    current_section = {
                        'type': 'summary',
                        'title': 'Profile',
                    }
                current_content.append(stripped)

        # Save the last section
        save_current_section()

        return sections

    def _extract_bullets(self, section_content: str, section_metadata: dict) -> list[dict]:
        """Extract individual bullet points from a section."""
        bullets = []
        lines = section_content.split('\n')

        current_bullet = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_bullet:
                    bullet_text = ' '.join(current_bullet)
                    if len(bullet_text) > 20:  # Skip very short bullets
                        bullets.append({
                            'bullet_text': bullet_text,
                            'company_name': section_metadata.get('company_name'),
                            'job_title': section_metadata.get('job_title'),
                            'skills_mentioned': self._extract_skills(bullet_text),
                        })
                    current_bullet = []
                continue

            # Check if line starts with bullet marker
            if re.match(r'^[-•*▪◦→]|\d+[.)]\s', stripped):
                if current_bullet:
                    bullet_text = ' '.join(current_bullet)
                    if len(bullet_text) > 20:
                        bullets.append({
                            'bullet_text': bullet_text,
                            'company_name': section_metadata.get('company_name'),
                            'job_title': section_metadata.get('job_title'),
                            'skills_mentioned': self._extract_skills(bullet_text),
                        })
                current_bullet = [re.sub(r'^[-•*▪◦→]|\d+[.)]\s*', '', stripped)]
            elif current_bullet:
                current_bullet.append(stripped)
            else:
                current_bullet = [stripped]

        # Save last bullet
        if current_bullet:
            bullet_text = ' '.join(current_bullet)
            if len(bullet_text) > 20:
                bullets.append({
                    'bullet_text': bullet_text,
                    'company_name': section_metadata.get('company_name'),
                    'job_title': section_metadata.get('job_title'),
                    'skills_mentioned': self._extract_skills(bullet_text),
                })

        return bullets

    def _extract_skills(self, text: str) -> list[str]:
        """Extract skill keywords from text."""
        # Common technical skills to look for
        skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|FastAPI|Spring|Rails)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Jenkins|CI/CD)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka)\b',
            r'\b(Machine Learning|Deep Learning|NLP|Computer Vision|AI)\b',
            r'\b(Agile|Scrum|Kanban|DevOps|SRE)\b',
            r'\b(Leadership|Management|Strategy|Communication)\b',
        ]

        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(m.lower() if isinstance(m, str) else m[0].lower() for m in matches)

        return list(skills)

    async def index_cv(
        self,
        cv_version_id: str,
        user_email: str,
        cv_content: str,
        version_name: str = None,
    ) -> dict:
        """
        Extract and store sections from CV content.

        Args:
            cv_version_id: Airtable cv_versions record ID
            user_email: User's email
            cv_content: Raw CV text content
            version_name: Optional version name

        Returns:
            Dict with indexing results
        """
        pool = await self.get_pool()
        content_hash = self._compute_hash(cv_content)

        async with pool.acquire() as conn:
            # Check if already indexed with same content
            existing = await conn.fetchrow(
                """
                SELECT id, content_hash FROM cv_extracted_content
                WHERE cv_version_id = $1
                """,
                cv_version_id
            )

            if existing and existing['content_hash'] == content_hash:
                logger.info(f"CV {cv_version_id} already indexed with same content")
                return {
                    'status': 'skipped',
                    'reason': 'already_indexed',
                    'cv_version_id': cv_version_id,
                }

            # Start transaction
            async with conn.transaction():
                # Delete existing content if re-indexing
                if existing:
                    await conn.execute(
                        "DELETE FROM cv_extracted_content WHERE id = $1",
                        existing['id']
                    )

                # Insert main content record
                content_id = await conn.fetchval(
                    """
                    INSERT INTO cv_extracted_content
                    (cv_version_id, user_email, version_name, raw_content, content_hash)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    cv_version_id, user_email, version_name, cv_content, content_hash
                )

                # Extract and insert sections
                sections = self.extract_sections(cv_content)
                section_count = 0
                bullet_count = 0

                for section in sections:
                    section_id = await conn.fetchval(
                        """
                        INSERT INTO cv_sections
                        (cv_content_id, section_type, section_title, content, position_order, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING id
                        """,
                        content_id,
                        section['section_type'],
                        section['section_title'],
                        section['content'],
                        section['position_order'],
                        '{}',
                    )
                    section_count += 1

                    # Extract bullets for experience sections
                    if section['section_type'] in ('experience', 'projects'):
                        bullets = self._extract_bullets(section['content'], {})
                        for bullet in bullets:
                            await conn.execute(
                                """
                                INSERT INTO cv_experience_bullets
                                (section_id, bullet_text, company_name, job_title, skills_mentioned)
                                VALUES ($1, $2, $3, $4, $5)
                                """,
                                section_id,
                                bullet['bullet_text'],
                                bullet.get('company_name'),
                                bullet.get('job_title'),
                                bullet.get('skills_mentioned', []),
                            )
                            bullet_count += 1

        logger.info(
            f"Indexed CV {cv_version_id}: {section_count} sections, {bullet_count} bullets"
        )

        return {
            'status': 'indexed',
            'cv_version_id': cv_version_id,
            'sections_count': section_count,
            'bullets_count': bullet_count,
        }

    async def get_all_content(self, user_email: str) -> list[dict]:
        """
        Get all indexed CV content for a user.

        Args:
            user_email: User's email

        Returns:
            List of CV content records with sections
        """
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            content_records = await conn.fetch(
                """
                SELECT
                    c.cv_version_id,
                    c.version_name,
                    c.indexed_at,
                    s.section_type,
                    s.section_title,
                    s.content,
                    s.position_order
                FROM cv_extracted_content c
                JOIN cv_sections s ON s.cv_content_id = c.id
                WHERE c.user_email = $1
                ORDER BY c.indexed_at DESC, s.position_order
                """,
                user_email
            )

        # Group by CV version
        cvs = {}
        for row in content_records:
            vid = row['cv_version_id']
            if vid not in cvs:
                cvs[vid] = {
                    'cv_version_id': vid,
                    'version_name': row['version_name'],
                    'indexed_at': row['indexed_at'].isoformat() if row['indexed_at'] else None,
                    'sections': [],
                }
            cvs[vid]['sections'].append({
                'section_type': row['section_type'],
                'section_title': row['section_title'],
                'content': row['content'],
                'position_order': row['position_order'],
            })

        return list(cvs.values())

    async def search_sections(
        self,
        user_email: str,
        query: str,
        section_types: list[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """
        Full-text search across CV sections.

        Args:
            user_email: User's email
            query: Search query
            section_types: Optional list of section types to filter
            limit: Max results

        Returns:
            List of matching sections with relevance scores
        """
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            if section_types:
                results = await conn.fetch(
                    """
                    SELECT
                        c.cv_version_id,
                        c.version_name,
                        s.section_type,
                        s.section_title,
                        s.content,
                        ts_rank(s.search_vector, websearch_to_tsquery('english', $2)) AS rank
                    FROM cv_extracted_content c
                    JOIN cv_sections s ON s.cv_content_id = c.id
                    WHERE c.user_email = $1
                      AND s.section_type = ANY($3)
                      AND s.search_vector @@ websearch_to_tsquery('english', $2)
                    ORDER BY rank DESC
                    LIMIT $4
                    """,
                    user_email, query, section_types, limit
                )
            else:
                results = await conn.fetch(
                    """
                    SELECT
                        c.cv_version_id,
                        c.version_name,
                        s.section_type,
                        s.section_title,
                        s.content,
                        ts_rank(s.search_vector, websearch_to_tsquery('english', $2)) AS rank
                    FROM cv_extracted_content c
                    JOIN cv_sections s ON s.cv_content_id = c.id
                    WHERE c.user_email = $1
                      AND s.search_vector @@ websearch_to_tsquery('english', $2)
                    ORDER BY rank DESC
                    LIMIT $3
                    """,
                    user_email, query, limit
                )

        return [
            {
                'cv_version_id': r['cv_version_id'],
                'version_name': r['version_name'],
                'section_type': r['section_type'],
                'section_title': r['section_title'],
                'content': r['content'],
                'relevance_score': float(r['rank']),
            }
            for r in results
        ]

    async def build_unified_experience(
        self,
        user_email: str,
        skills_filter: list[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Merge all experience bullets from all CV versions.

        Args:
            user_email: User's email
            skills_filter: Optional list of skills to filter by
            limit: Max bullets to return

        Returns:
            Dict with unified experience data
        """
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            if skills_filter:
                bullets = await conn.fetch(
                    """
                    SELECT DISTINCT ON (b.bullet_text)
                        c.cv_version_id,
                        c.version_name,
                        b.bullet_text,
                        b.company_name,
                        b.job_title,
                        b.skills_mentioned
                    FROM cv_extracted_content c
                    JOIN cv_sections s ON s.cv_content_id = c.id
                    JOIN cv_experience_bullets b ON b.section_id = s.id
                    WHERE c.user_email = $1
                      AND b.skills_mentioned && $2
                    ORDER BY b.bullet_text, c.indexed_at DESC
                    LIMIT $3
                    """,
                    user_email, skills_filter, limit
                )
            else:
                bullets = await conn.fetch(
                    """
                    SELECT DISTINCT ON (b.bullet_text)
                        c.cv_version_id,
                        c.version_name,
                        b.bullet_text,
                        b.company_name,
                        b.job_title,
                        b.skills_mentioned
                    FROM cv_extracted_content c
                    JOIN cv_sections s ON s.cv_content_id = c.id
                    JOIN cv_experience_bullets b ON b.section_id = s.id
                    WHERE c.user_email = $1
                    ORDER BY b.bullet_text, c.indexed_at DESC
                    LIMIT $2
                    """,
                    user_email, limit
                )

            # Also get all summaries
            summaries = await conn.fetch(
                """
                SELECT DISTINCT ON (s.content)
                    c.cv_version_id,
                    c.version_name,
                    s.content
                FROM cv_extracted_content c
                JOIN cv_sections s ON s.cv_content_id = c.id
                WHERE c.user_email = $1
                  AND s.section_type = 'summary'
                ORDER BY s.content, c.indexed_at DESC
                LIMIT 10
                """,
                user_email
            )

            # Get all skills sections
            skills = await conn.fetch(
                """
                SELECT DISTINCT ON (s.content)
                    c.cv_version_id,
                    s.content
                FROM cv_extracted_content c
                JOIN cv_sections s ON s.cv_content_id = c.id
                WHERE c.user_email = $1
                  AND s.section_type = 'skills'
                ORDER BY s.content, c.indexed_at DESC
                LIMIT 10
                """,
                user_email
            )

        return {
            'experience_bullets': [
                {
                    'cv_version_id': b['cv_version_id'],
                    'version_name': b['version_name'],
                    'bullet_text': b['bullet_text'],
                    'company_name': b['company_name'],
                    'job_title': b['job_title'],
                    'skills_mentioned': b['skills_mentioned'],
                }
                for b in bullets
            ],
            'summaries': [
                {
                    'cv_version_id': s['cv_version_id'],
                    'version_name': s['version_name'],
                    'content': s['content'],
                }
                for s in summaries
            ],
            'skills_sections': [
                {
                    'cv_version_id': s['cv_version_id'],
                    'content': s['content'],
                }
                for s in skills
            ],
            'total_bullets': len(bullets),
            'total_summaries': len(summaries),
        }

    async def get_indexed_versions(self, user_email: str) -> list[dict]:
        """
        List all indexed CV versions for a user.

        Args:
            user_email: User's email

        Returns:
            List of indexed version summaries
        """
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            versions = await conn.fetch(
                """
                SELECT
                    c.cv_version_id,
                    c.version_name,
                    c.indexed_at,
                    COUNT(DISTINCT s.id) AS section_count,
                    COUNT(DISTINCT b.id) AS bullet_count
                FROM cv_extracted_content c
                LEFT JOIN cv_sections s ON s.cv_content_id = c.id
                LEFT JOIN cv_experience_bullets b ON b.section_id = s.id
                WHERE c.user_email = $1
                GROUP BY c.cv_version_id, c.version_name, c.indexed_at
                ORDER BY c.indexed_at DESC
                """,
                user_email
            )

        return [
            {
                'cv_version_id': v['cv_version_id'],
                'version_name': v['version_name'],
                'indexed_at': v['indexed_at'].isoformat() if v['indexed_at'] else None,
                'section_count': v['section_count'],
                'bullet_count': v['bullet_count'],
            }
            for v in versions
        ]

    async def delete_cv_index(self, cv_version_id: str, user_email: str) -> bool:
        """
        Delete indexed content for a CV version.

        Args:
            cv_version_id: Airtable cv_versions record ID
            user_email: User's email (for ownership verification)

        Returns:
            True if deleted, False if not found
        """
        pool = await self.get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM cv_extracted_content
                WHERE cv_version_id = $1 AND user_email = $2
                """,
                cv_version_id, user_email
            )

        deleted = result.split()[-1] != '0'
        if deleted:
            logger.info(f"Deleted index for CV {cv_version_id}")
        return deleted


# Global singleton instance
_knowledge_base: Optional[CVKnowledgeBase] = None


def get_knowledge_base() -> CVKnowledgeBase:
    """Get the global CVKnowledgeBase instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = CVKnowledgeBase()
    return _knowledge_base

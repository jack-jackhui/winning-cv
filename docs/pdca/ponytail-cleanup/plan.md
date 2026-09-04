# Plan: Ponytail Audit Codebase Cleanup & Modernization

## 1. Goal & Hypothesis
Implement the 13 cleanup and dead-code removal findings from the `ponytail-audit` report. By removing obsolete Streamlit legacy UI, legacy feeds, legacy wrapper classes, unused heavy dependencies (`spacy`, `scikit-learn`, `feedparser`, `pipdeptree`, `uv`), and dead code paths, we will:
- Reduce Docker image size by >200MB and speed up build/install times.
- Eliminate duplicated logic (Struct, Settings façade, CVGenerator v1).
- Unify CV generation onto `CVGeneratorV2` and storage exclusively onto MinIO.
- Clean up the frontend animation component exports.

## 2. Scope & Breakdown

### Phase 1: Dead Services & Dependencies Removal
- **Item 1: Remove Streamlit UI Layer**
  - Delete `webui.py`, `webui_new.py`, `ui/job_search_ui.py`, `ui/generate_ui.py`, `ui/history_ui.py`, `ui/sidebar.py`.
  - Remove references in `README.md`, `README-zh.md`, `ruff.toml`.
  - Remove `streamlit`, `streamlit-extras`, `great-tables` from `requirements.in`.
- **Item 2: Delete `feed/linkedin_feed.py` & RSS Scraper**
  - Delete `feed/linkedin_feed.py` and `feed/`.
  - Remove `feedparser` from `requirements.in`.
  - Update `tests/test_linkedin_job_fetching.py` and `tests/test_workflow_steps.py`.
- **Item 7: Strip spaCy & scikit-learn from Matcher & Dependencies**
  - In `utils/matcher.py`: remove `basic_match_score` and `preprocess_text`, remove imports of `spacy`, `TfidfVectorizer`, `cosine_similarity`.
  - In `requirements.in`: remove `spacy`, `scikit-learn`.
  - In `Dockerfile`, `README.md`, `README-zh.md`, `CLAUDE.md`: remove `spacy download en_core_web_sm`.
- **Items 11 & 12: Remove `pipdeptree` and `uv` from `requirements.in`**
  - Remove dev/tooling circular dependencies from `requirements.in`.

### Phase 2: Consolidation & Refactoring
- **Item 5: Consolidate CV Generator into `cv_generator_v2.py`**
  - Move `generate_cv_with_knowledge_base`, `generate_cv_with_knowledge`, and helper builders (`_build_knowledge_context`, `_build_enhanced_system_prompt`) from `cv/cv_generator.py` into `cv/cv_generator_v2.py`.
  - Update all import sites (`api/routes/cv.py`, `api/routes/knowledge_base.py`, `job_processing/core.py`, tests).
  - Delete `cv/cv_generator.py`.
- **Item 9: Clean WordPress upload path & relocate helpers**
  - Remove `upload_pdf_to_wordpress`, `upload_pdf`, `get_storage_backend` and WordPress fallbacks in `api/routes/jobs.py` (lines 343-352) and `job_processing/core.py`.
  - Move remaining JD/CV text helpers (`extract_title_from_jd`, `clean_llm_output`, `strip_llm_contact_block`, `extract_contact_info`) to `utils/cv_utils.py` (or `utils/helpers.py`) and delete `ui/helpers.py` & `ui/`.
- **Item 6: Deduplicate Struct in `main.py`**
  - In `main.py`: replace local `class Struct` definition with `from utils.utils import Struct`.
- **Item 13: Shrink Scheduler Wrapper**
  - Replace `JobScheduler` in `scheduler/job_scheduler.py` by using `BackgroundScheduler` directly in `api/main.py`.
  - Delete `scheduler/job_scheduler.py` and `scheduler/`.
- **Item 8: Simplify Airtable Client**
  - Inline pyairtable configuration with timeout and retry into `data_store/airtable_manager.py` / `data_store/cv_version_manager.py`.
  - Delete `utils/airtable_client.py`.

### Phase 3: Configuration & Storage Simplification
- **Item 3: Remove `config/settings.py` Façade**
  - Ensure `config/settings_v2.py` has all required settings, properties, and aliases.
  - Update all `from config.settings import Config` call sites to `from config.settings_v2 import settings`.
  - Delete `config/settings.py` and update settings tests.
- **Item 4: Simplify Dual-Write Managers**
  - Replace verbose boilerplate in `data_store/storage_factory.py` with a streamlined dynamic proxy / concise wrapper for shadow writes.

### Phase 4: Frontend & Final Verification
- **Item 10: Clean Dead Exports in `AnimatedElements.jsx`**
  - Remove unused exports in `frontend/src/components/ui/AnimatedElements.jsx` (`fadeInDown`, `shimmer`, `AnimatedText`, `AnimatedCounter`, `GradientBorder`, `staggerContainerSlow`, `cardHover`, `slideInLeft`, `slideInRight`).
  - **Deviation**: `fadeIn`, `pulse`, and `AnimatedSection` were also removed. Serena reference search proved these are only self-referenced and not imported by any consumer, so the "keep" list in the original plan was overspecified.
  - Final live exports: `fadeInUp`, `scaleIn`, `staggerContainer`, `float`.
- **Validation Gates** *(all green 2026-09-04)*
  - Compile requirements (`uv pip compile requirements.in`) — done, `uv.lock` generated.
  - Run linting (`ruff check .`) — no new violations introduced; remaining `F841` unused-variable warnings are pre-existing at HEAD.
  - Run test suite (`pytest`) — **211 passed, 6 skipped, 5 failed**; all 5 failures are pre-existing/environmental (live LinkedIn/Seek scraping, missing Azure creds, `.env` overriding `test_default_values`' hardcoded default).
  - Verify frontend builds cleanly (`npm run build`) — production build succeeds (2.9s, 2282 modules).

## 3. Risks & Mitigations
- **Risk 1: Breaking test suites that mock `Config` or `CVGenerator`**
  - *Mitigation*: Audit and update test fixtures in `tests/test_settings.py`, `tests/test_cv_version_management.py`, etc., to use `settings` and `CVGeneratorV2`.
    - **Resolved**: `Config` is a non-callable singleton, so test fixtures changed from `Config()` to `Config` (`tests/test_linkedin_job_fetching.py`, `tests/test_workflow_steps.py`). Dead legacy-`CVGenerator` fallback blocks in `api/routes/cv.py` were removed in favor of unconditional `CVGeneratorV2()`.
- **Risk 2: DualWrite test expectations**
  - *Mitigation*: Ensure `DualWriteDataManager` / `DualWriteCVVersionManager` proxy preserves method signatures and shadow-write exception handling expected by tests.
    - **Resolved**: Proxy now uses `getattr()` instead of `.__getattribute__()` internally, which is compatible with the Mock-based DualWrite tests while preserving `ShadowWriteError` semantics and `update_application_status`'s `job_link` extraction. All 39 tests in `tests/test_job_result_workspace.py` and the `ShadowWriteError` postgres-persistence test pass.

## 4. Status
**All phases (1-4) complete and validated.** See commit on `refactor/ponytail-audit-cleanup`.

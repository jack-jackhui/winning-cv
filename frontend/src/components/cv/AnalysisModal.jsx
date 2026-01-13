import { useState } from 'react'
import {
  X,
  ChevronDown,
  ChevronUp,
  Target,
  Award,
  Briefcase,
  Bot,
  AlertTriangle,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Minus,
} from 'lucide-react'

/**
 * Score bar component for displaying scores with color coding
 */
function ScoreBar({ score, label }) {
  const getScoreColor = (score) => {
    if (score >= 90) return 'bg-emerald-500'
    if (score >= 75) return 'bg-blue-500'
    if (score >= 60) return 'bg-amber-500'
    return 'bg-red-500'
  }

  const getScoreLabel = (score) => {
    if (score >= 90) return 'Excellent'
    if (score >= 75) return 'Strong'
    if (score >= 60) return 'Moderate'
    if (score >= 40) return 'Weak'
    return 'Poor'
  }

  return (
    <div className="space-y-1">
      {label && <div className="text-sm text-text-secondary">{label}</div>}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2.5 bg-surface-elevated rounded-full overflow-hidden">
          <div
            className={`h-full ${getScoreColor(score)} transition-all duration-500`}
            style={{ width: `${score}%` }}
          />
        </div>
        <span className="text-sm font-medium text-text-primary w-16 text-right">
          {score}%
        </span>
        <span className="text-xs text-text-muted w-16">
          {getScoreLabel(score)}
        </span>
      </div>
    </div>
  )
}

/**
 * Collapsible section component
 */
function CollapsibleSection({ title, icon: Icon, score, children, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between bg-surface-elevated hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-accent-500" />
          <span className="font-medium text-text-primary">{title}</span>
          {score !== undefined && (
            <span className="text-sm text-text-muted">({score}%)</span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-text-muted" />
        ) : (
          <ChevronDown className="w-5 h-5 text-text-muted" />
        )}
      </button>
      {isOpen && (
        <div className="px-4 py-4 space-y-3 bg-surface">
          {children}
        </div>
      )}
    </div>
  )
}

/**
 * List with icons for matched/missing items
 */
function ItemList({ items, type = 'matched' }) {
  if (!items || items.length === 0) {
    return <span className="text-sm text-text-muted italic">None</span>
  }

  const Icon = type === 'matched' ? CheckCircle2 : type === 'missing' ? XCircle : Minus
  const colorClass = type === 'matched' ? 'text-emerald-400' : type === 'missing' ? 'text-red-400' : 'text-amber-400'

  return (
    <ul className="space-y-1.5">
      {items.map((item, idx) => (
        <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
          <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${colorClass}`} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

/**
 * CV-JD Fit Analysis Modal
 */
export default function AnalysisModal({ analysis, onClose }) {
  if (!analysis) return null

  const {
    overall_score,
    summary,
    keyword_match,
    skills_coverage,
    experience_relevance,
    ats_optimization,
    gap_analysis,
    talking_points,
  } = analysis

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl max-h-[90vh] bg-surface rounded-xl shadow-2xl border border-border flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-xl font-semibold text-text-primary">CV-JD Fit Analysis</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Overall Score */}
          <div className="text-center p-6 rounded-xl bg-surface-elevated">
            <div className="text-sm text-text-muted mb-2">Overall Match Score</div>
            <div className="text-5xl font-bold text-text-primary mb-2">
              {overall_score}%
            </div>
            <ScoreBar score={overall_score} />
            {summary && (
              <p className="mt-4 text-text-secondary text-sm leading-relaxed">
                {summary}
              </p>
            )}
          </div>

          {/* Keyword Match */}
          {keyword_match && (
            <CollapsibleSection
              title="Keyword Match"
              icon={Target}
              score={keyword_match.score}
              defaultOpen={true}
            >
              <ScoreBar score={keyword_match.score} />
              <div className="mt-3 text-sm text-text-muted">
                Density: <span className="text-text-primary">{keyword_match.density_assessment}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-3">
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Matched Keywords</div>
                  <ItemList items={keyword_match.matched} type="matched" />
                </div>
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Missing Keywords</div>
                  <ItemList items={keyword_match.missing} type="missing" />
                </div>
              </div>
            </CollapsibleSection>
          )}

          {/* Skills Coverage */}
          {skills_coverage && (
            <CollapsibleSection
              title="Skills Coverage"
              icon={Award}
              score={skills_coverage.score}
            >
              <ScoreBar score={skills_coverage.score} />
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Technical Skills</div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-text-muted mb-1">Matched</div>
                      <ItemList items={skills_coverage.technical_skills?.matched} type="matched" />
                    </div>
                    <div>
                      <div className="text-xs text-text-muted mb-1">Missing</div>
                      <ItemList items={skills_coverage.technical_skills?.missing} type="missing" />
                    </div>
                  </div>
                  {skills_coverage.technical_skills?.partial?.length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs text-text-muted mb-1">Partial Match</div>
                      <ItemList items={skills_coverage.technical_skills.partial} type="partial" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Soft Skills</div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-text-muted mb-1">Matched</div>
                      <ItemList items={skills_coverage.soft_skills?.matched} type="matched" />
                    </div>
                    <div>
                      <div className="text-xs text-text-muted mb-1">Demonstrated</div>
                      <ItemList items={skills_coverage.soft_skills?.demonstrated} type="matched" />
                    </div>
                  </div>
                </div>
              </div>
            </CollapsibleSection>
          )}

          {/* Experience Relevance */}
          {experience_relevance && (
            <CollapsibleSection
              title="Experience Relevance"
              icon={Briefcase}
              score={experience_relevance.score}
            >
              <ScoreBar score={experience_relevance.score} />
              <div className="mt-3 text-sm text-text-muted">
                Years Alignment: <span className="text-text-primary">{experience_relevance.years_alignment}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-3">
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Aligned Roles</div>
                  <ItemList items={experience_relevance.aligned_roles} type="matched" />
                </div>
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">Key Achievements</div>
                  <ItemList items={experience_relevance.relevant_achievements} type="matched" />
                </div>
              </div>
            </CollapsibleSection>
          )}

          {/* ATS Optimization */}
          {ats_optimization && (
            <CollapsibleSection
              title="ATS Optimization"
              icon={Bot}
              score={ats_optimization.score}
            >
              <ScoreBar score={ats_optimization.score} />
              <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-text-muted">Format</div>
                  <div className={ats_optimization.format_check ? 'text-emerald-400' : 'text-red-400'}>
                    {ats_optimization.format_check ? 'Clean' : 'Needs Work'}
                  </div>
                </div>
                <div>
                  <div className="text-text-muted">Keyword Density</div>
                  <div className="text-text-primary">{ats_optimization.keyword_density}</div>
                </div>
                <div>
                  <div className="text-text-muted">Structure</div>
                  <div className="text-text-primary">{ats_optimization.section_structure}</div>
                </div>
              </div>
              {ats_optimization.recommendations?.length > 0 && (
                <div className="mt-3">
                  <div className="text-sm font-medium text-text-primary mb-2">Recommendations</div>
                  <ItemList items={ats_optimization.recommendations} type="partial" />
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Gap Analysis */}
          {gap_analysis && (gap_analysis.critical_gaps?.length > 0 || gap_analysis.minor_gaps?.length > 0) && (
            <CollapsibleSection
              title="Gap Analysis"
              icon={AlertTriangle}
            >
              {gap_analysis.critical_gaps?.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-red-400 mb-2">Critical Gaps</div>
                  <ItemList items={gap_analysis.critical_gaps} type="missing" />
                </div>
              )}
              {gap_analysis.minor_gaps?.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-amber-400 mb-2">Minor Gaps</div>
                  <ItemList items={gap_analysis.minor_gaps} type="partial" />
                </div>
              )}
              {gap_analysis.mitigation_suggestions?.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">How to Address</div>
                  <ItemList items={gap_analysis.mitigation_suggestions} type="matched" />
                </div>
              )}
            </CollapsibleSection>
          )}

          {/* Talking Points */}
          {talking_points && (
            <CollapsibleSection
              title="Interview Talking Points"
              icon={MessageSquare}
              defaultOpen={true}
            >
              {talking_points.strengths_to_highlight?.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-emerald-400 mb-2">Strengths to Highlight</div>
                  <ItemList items={talking_points.strengths_to_highlight} type="matched" />
                </div>
              )}
              {talking_points.questions_to_prepare?.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-text-primary mb-2">Questions to Prepare</div>
                  <ItemList items={talking_points.questions_to_prepare} type="partial" />
                </div>
              )}
              {talking_points.stories_to_ready?.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-text-primary mb-2">STAR Stories to Ready</div>
                  <ItemList items={talking_points.stories_to_ready} type="matched" />
                </div>
              )}
            </CollapsibleSection>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="w-full btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

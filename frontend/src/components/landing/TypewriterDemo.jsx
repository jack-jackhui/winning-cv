import { motion, useInView } from 'framer-motion'
import { useRef, useState, useEffect } from 'react'
import { Sparkles, Copy, Check, RefreshCw } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const cvExamples = [
  {
    title: 'Software Engineer',
    original:
      'Experienced developer with programming skills. Worked on various projects and teams.',
    optimized:
      'Results-driven Software Engineer with 5+ years architecting scalable microservices, reducing system latency by 40% and increasing deployment frequency by 3x through CI/CD automation.',
  },
  {
    title: 'Product Manager',
    original:
      'Product manager who has launched products and worked with teams to deliver features.',
    optimized:
      'Strategic Product Manager who drove $2.4M ARR growth through data-driven roadmap prioritization, achieving 94% on-time delivery while reducing feature cycle time by 35%.',
  },
  {
    title: 'Data Analyst',
    original:
      'Analyst experienced with data tools and creating reports for stakeholders.',
    optimized:
      'Impact-focused Data Analyst transforming 10TB+ datasets into actionable insights, automating 20+ weekly reports saving 15 hours/week, and enabling $500K cost optimization.',
  },
]

function TypewriterText({ text, isTyping, onComplete }) {
  const [displayText, setDisplayText] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (!isTyping) {
      setDisplayText('')
      setCurrentIndex(0)
      return
    }

    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText(text.slice(0, currentIndex + 1))
        setCurrentIndex(currentIndex + 1)
      }, 20 + Math.random() * 30) // Variable speed for natural feel

      return () => clearTimeout(timeout)
    } else if (onComplete) {
      onComplete()
    }
  }, [isTyping, currentIndex, text, onComplete])

  return (
    <span>
      {displayText}
      {isTyping && currentIndex < text.length && (
        <motion.span
          className="inline-block w-0.5 h-5 bg-accent-400 ml-0.5"
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
        />
      )}
    </span>
  )
}

export default function TypewriterDemo() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })
  const [activeExample, setActiveExample] = useState(0)
  const [phase, setPhase] = useState('idle') // idle, analyzing, typing, complete
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (isInView && phase === 'idle') {
      startAnimation()
    }
  }, [isInView, phase])

  const startAnimation = () => {
    setPhase('analyzing')
    setTimeout(() => {
      setPhase('typing')
    }, 1500)
  }

  const handleTypingComplete = () => {
    setPhase('complete')
  }

  const handleReset = () => {
    setPhase('idle')
    setActiveExample((prev) => (prev + 1) % cvExamples.length)
    setTimeout(() => startAnimation(), 100)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(cvExamples[activeExample].optimized)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const currentExample = cvExamples[activeExample]

  return (
    <section className="relative overflow-hidden bg-surface/30">
      <div className="container-default section-padding">
        {/* Header */}
        <motion.div
          className="text-center max-w-2xl mx-auto mb-16"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={staggerContainer}
        >
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6"
            variants={fadeInUp}
          >
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-400">
              AI in Action
            </span>
          </motion.div>
          <motion.h2
            className="text-3xl sm:text-4xl font-bold text-text-primary"
            variants={fadeInUp}
          >
            Watch AI transform your CV
          </motion.h2>
          <motion.p
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            See how our AI rewrites generic descriptions into impactful,
            job-winning content
          </motion.p>
        </motion.div>

        {/* Demo Area */}
        <div ref={ref} className="max-w-4xl mx-auto">
          {/* Role selector */}
          <motion.div
            className="flex flex-wrap justify-center gap-2 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
          >
            {cvExamples.map((example, index) => (
              <button
                key={example.title}
                onClick={() => {
                  if (index !== activeExample) {
                    setActiveExample(index)
                    setPhase('idle')
                    setTimeout(() => startAnimation(), 100)
                  }
                }}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  index === activeExample
                    ? 'bg-accent-500 text-white'
                    : 'bg-surface border border-border text-text-muted hover:text-text-primary hover:border-accent-500/50'
                }`}
              >
                {example.title}
              </button>
            ))}
          </motion.div>

          {/* Main demo container */}
          <motion.div
            className="grid md:grid-cols-2 gap-6"
            initial={{ opacity: 0, y: 30 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2 }}
          >
            {/* Original CV */}
            <div className="relative">
              <div className="absolute -top-3 left-4 px-3 py-1 bg-surface rounded-full border border-border">
                <span className="text-xs font-medium text-text-muted">
                  Original
                </span>
              </div>
              <div className="h-full p-6 rounded-2xl bg-background border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-2 h-2 rounded-full bg-red-400" />
                  <div className="w-2 h-2 rounded-full bg-yellow-400" />
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                </div>
                <p className="text-text-secondary leading-relaxed font-mono text-sm">
                  {currentExample.original}
                </p>
              </div>
            </div>

            {/* Optimized CV */}
            <div className="relative">
              <div className="absolute -top-3 left-4 px-3 py-1 bg-accent-500/10 rounded-full border border-accent-500/30">
                <span className="text-xs font-medium text-accent-400">
                  AI Optimized
                </span>
              </div>
              <div className="h-full p-6 rounded-2xl bg-background border border-accent-500/30 relative overflow-hidden">
                {/* Gradient glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-accent-500/5 to-purple-500/5" />

                <div className="relative">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-2 rounded-full bg-red-400" />
                    <div className="w-2 h-2 rounded-full bg-yellow-400" />
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                  </div>

                  {/* Analyzing state */}
                  {phase === 'analyzing' && (
                    <motion.div
                      className="flex items-center gap-3 text-accent-400"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    >
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          ease: 'linear',
                        }}
                      >
                        <Sparkles className="w-5 h-5" />
                      </motion.div>
                      <span className="text-sm font-medium">
                        Analyzing job requirements...
                      </span>
                    </motion.div>
                  )}

                  {/* Typing state */}
                  {(phase === 'typing' || phase === 'complete') && (
                    <p className="text-text-primary leading-relaxed font-mono text-sm min-h-[100px]">
                      <TypewriterText
                        text={currentExample.optimized}
                        isTyping={phase === 'typing'}
                        onComplete={handleTypingComplete}
                      />
                    </p>
                  )}

                  {/* Idle state */}
                  {phase === 'idle' && (
                    <p className="text-text-muted leading-relaxed font-mono text-sm">
                      Click to see the magic...
                    </p>
                  )}
                </div>

                {/* Action buttons */}
                {phase === 'complete' && (
                  <motion.div
                    className="flex items-center gap-2 mt-4 pt-4 border-t border-border/50"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent-500/10 text-accent-400 text-sm hover:bg-accent-500/20 transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-4 h-4" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copy
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleReset}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface text-text-muted text-sm hover:text-text-primary transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Try another
                    </button>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Feature highlights */}
          <motion.div
            className="mt-12 grid sm:grid-cols-3 gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.4 }}
          >
            {[
              {
                title: 'Keyword Optimization',
                description: 'Matches job-specific terminology',
              },
              {
                title: 'Impact Metrics',
                description: 'Adds quantifiable achievements',
              },
              {
                title: 'ATS-Friendly',
                description: 'Formatted for tracking systems',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="text-center p-4 rounded-xl bg-surface/50 border border-border/50"
              >
                <div className="text-sm font-medium text-text-primary">
                  {feature.title}
                </div>
                <div className="text-xs text-text-muted mt-1">
                  {feature.description}
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}

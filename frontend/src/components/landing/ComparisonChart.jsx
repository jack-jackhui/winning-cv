import { motion, useInView } from 'framer-motion'
import { useRef, useState, useEffect } from 'react'
import { TrendingUp, Clock, Target, Award } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const comparisonData = [
  {
    metric: 'Job Match Rate',
    without: 15,
    with: 78,
    icon: Target,
    suffix: '%',
    description: 'Relevant job matches',
  },
  {
    metric: 'Application Time',
    without: 45,
    with: 5,
    icon: Clock,
    suffix: 'min',
    description: 'Per application',
    inverse: true, // Lower is better
  },
  {
    metric: 'Interview Rate',
    without: 8,
    with: 42,
    icon: TrendingUp,
    suffix: '%',
    description: 'Callback success',
  },
  {
    metric: 'ATS Score',
    without: 45,
    with: 92,
    icon: Award,
    suffix: '%',
    description: 'Compatibility rating',
  },
]

function AnimatedBar({ value, maxValue, color, delay, isInView }) {
  const percentage = (value / maxValue) * 100

  return (
    <div className="relative h-8 bg-background/50 rounded-lg overflow-hidden">
      <motion.div
        className={`absolute inset-y-0 left-0 ${color} rounded-lg`}
        initial={{ width: 0 }}
        animate={isInView ? { width: `${percentage}%` } : { width: 0 }}
        transition={{
          duration: 1,
          delay: delay,
          ease: [0.22, 1, 0.36, 1],
        }}
      />
      <motion.div
        className="absolute inset-0 flex items-center justify-end pr-3"
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : { opacity: 0 }}
        transition={{ delay: delay + 0.5 }}
      >
        <span className="text-sm font-semibold text-text-primary">
          {value}
        </span>
      </motion.div>
    </div>
  )
}

function AnimatedNumber({ value, suffix, delay, isInView }) {
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    if (!isInView) return

    const duration = 1500
    const startTime = Date.now() + delay * 1000
    const endValue = value

    const animate = () => {
      const now = Date.now()
      if (now < startTime) {
        requestAnimationFrame(animate)
        return
      }

      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Easing function
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(Math.round(eased * endValue))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [value, delay, isInView])

  return (
    <span>
      {displayValue}
      {suffix}
    </span>
  )
}

export default function ComparisonChart() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="relative overflow-hidden">
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
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-500/10 border border-green-500/20 mb-6"
            variants={fadeInUp}
          >
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-green-400">
              Data-Driven Results
            </span>
          </motion.div>
          <motion.h2
            className="text-3xl sm:text-4xl font-bold text-text-primary"
            variants={fadeInUp}
          >
            The WinningCV difference
          </motion.h2>
          <motion.p
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            See how AI-optimized CVs outperform traditional applications
          </motion.p>
        </motion.div>

        {/* Comparison Chart */}
        <div ref={ref} className="max-w-4xl mx-auto">
          {/* Legend */}
          <motion.div
            className="flex justify-center gap-8 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gray-500/50" />
              <span className="text-sm text-text-muted">Without WinningCV</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gradient-to-r from-accent-500 to-green-500" />
              <span className="text-sm text-text-muted">With WinningCV</span>
            </div>
          </motion.div>

          {/* Metrics */}
          <div className="space-y-8">
            {comparisonData.map((item, index) => (
              <motion.div
                key={item.metric}
                className="bg-surface/50 rounded-2xl p-6 border border-border/50"
                initial={{ opacity: 0, x: -30 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{
                  duration: 0.5,
                  delay: index * 0.1,
                }}
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-accent-500/10 flex items-center justify-center">
                    <item.icon className="w-5 h-5 text-accent-400" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-text-primary">
                        {item.metric}
                      </h3>
                      <span className="text-xs text-text-muted">
                        {item.description}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bars */}
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="w-24 text-right text-sm text-text-muted">
                      Traditional
                    </div>
                    <div className="flex-1">
                      <AnimatedBar
                        value={item.without}
                        maxValue={Math.max(item.without, item.with)}
                        color="bg-gray-500/50"
                        delay={index * 0.1}
                        isInView={isInView}
                      />
                    </div>
                    <div className="w-16 text-right">
                      <span className="text-sm font-medium text-text-muted">
                        <AnimatedNumber
                          value={item.without}
                          suffix={item.suffix}
                          delay={index * 0.1}
                          isInView={isInView}
                        />
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-24 text-right text-sm text-accent-400 font-medium">
                      WinningCV
                    </div>
                    <div className="flex-1">
                      <AnimatedBar
                        value={item.with}
                        maxValue={Math.max(item.without, item.with)}
                        color="bg-gradient-to-r from-accent-500 to-green-500"
                        delay={index * 0.1 + 0.2}
                        isInView={isInView}
                      />
                    </div>
                    <div className="w-16 text-right">
                      <span className="text-sm font-bold text-green-400">
                        <AnimatedNumber
                          value={item.with}
                          suffix={item.suffix}
                          delay={index * 0.1 + 0.2}
                          isInView={isInView}
                        />
                      </span>
                    </div>
                  </div>
                </div>

                {/* Improvement badge */}
                <motion.div
                  className="mt-4 flex justify-end"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={isInView ? { opacity: 1, scale: 1 } : {}}
                  transition={{ delay: index * 0.1 + 0.8 }}
                >
                  <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20">
                    <TrendingUp className="w-3 h-3 text-green-400" />
                    <span className="text-xs font-medium text-green-400">
                      {item.inverse
                        ? `${Math.round(((item.without - item.with) / item.without) * 100)}% faster`
                        : `${Math.round(((item.with - item.without) / item.without) * 100)}% improvement`}
                    </span>
                  </div>
                </motion.div>
              </motion.div>
            ))}
          </div>

          {/* Bottom CTA */}
          <motion.div
            className="mt-12 text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 1 }}
          >
            <p className="text-text-muted text-sm">
              Based on aggregated user data. Individual results may vary.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

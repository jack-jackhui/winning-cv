import { motion } from 'framer-motion'
import { FileText, Brain, Briefcase, FileCheck, ArrowRight } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const workflowSteps = [
  {
    id: 'upload',
    icon: FileText,
    label: 'Your CV',
    sublabel: 'Upload once',
    color: 'from-blue-500 to-blue-600',
  },
  {
    id: 'analyze',
    icon: Brain,
    label: 'AI Analysis',
    sublabel: 'Skills extracted',
    color: 'from-purple-500 to-purple-600',
  },
  {
    id: 'match',
    icon: Briefcase,
    label: 'Job Match',
    sublabel: 'Best fits found',
    color: 'from-accent-500 to-accent-600',
  },
  {
    id: 'generate',
    icon: FileCheck,
    label: 'Tailored CV',
    sublabel: 'Ready to apply',
    color: 'from-green-500 to-green-600',
  },
]

const nodeVariants = {
  hidden: { opacity: 0, scale: 0.5, y: 20 },
  visible: (i) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.5,
      delay: i * 0.15,
      type: 'spring',
      stiffness: 200,
      damping: 20,
    },
  }),
}

const connectionVariants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: (i) => ({
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: {
        duration: 0.8,
        delay: 0.3 + i * 0.15,
        ease: 'easeInOut',
      },
      opacity: { duration: 0.2, delay: 0.3 + i * 0.15 },
    },
  }),
}

const pulseVariants = {
  animate: {
    scale: [1, 1.2, 1],
    opacity: [0.5, 0.8, 0.5],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

const dataFlowVariants = {
  animate: (i) => ({
    x: [0, 100],
    opacity: [0, 1, 1, 0],
    transition: {
      duration: 1.5,
      delay: i * 0.15 + 1,
      repeat: Infinity,
      repeatDelay: 2,
      ease: 'easeInOut',
    },
  }),
}

export default function WorkflowDiagram() {
  return (
    <section className="relative overflow-hidden bg-surface/50">
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
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-500/10 border border-accent-500/20 mb-6"
            variants={fadeInUp}
          >
            <span className="text-sm font-medium text-accent-400">
              Intelligent Workflow
            </span>
          </motion.div>
          <motion.h2
            className="text-3xl sm:text-4xl font-bold text-text-primary"
            variants={fadeInUp}
          >
            From upload to application
          </motion.h2>
          <motion.p
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            Watch how your CV transforms into job-winning applications
          </motion.p>
        </motion.div>

        {/* Workflow Diagram */}
        <motion.div
          className="relative max-w-4xl mx-auto"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
        >
          {/* Background glow effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-accent-500/5 via-purple-500/5 to-green-500/5 blur-3xl" />

          {/* SVG Connection Lines */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none hidden md:block"
            viewBox="0 0 800 200"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgb(99, 102, 241)" />
                <stop offset="50%" stopColor="rgb(168, 85, 247)" />
                <stop offset="100%" stopColor="rgb(34, 197, 94)" />
              </linearGradient>
            </defs>
            {[0, 1, 2].map((i) => (
              <motion.path
                key={i}
                d={`M ${170 + i * 200} 100 Q ${220 + i * 200} 100 ${270 + i * 200} 100`}
                stroke="url(#lineGradient)"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                variants={connectionVariants}
                custom={i}
              />
            ))}
            {/* Animated data flow dots */}
            {[0, 1, 2].map((i) => (
              <motion.circle
                key={`dot-${i}`}
                r="4"
                fill="rgb(99, 102, 241)"
                custom={i}
                variants={dataFlowVariants}
                animate="animate"
                style={{
                  offsetPath: `path('M ${170 + i * 200} 100 Q ${220 + i * 200} 100 ${270 + i * 200} 100')`,
                }}
              >
                <animate
                  attributeName="cx"
                  from={170 + i * 200}
                  to={270 + i * 200}
                  dur="1.5s"
                  begin={`${i * 0.15 + 1}s`}
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0;1;1;0"
                  dur="1.5s"
                  begin={`${i * 0.15 + 1}s`}
                  repeatCount="indefinite"
                />
              </motion.circle>
            ))}
          </svg>

          {/* Nodes */}
          <div className="relative grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-4">
            {workflowSteps.map((step, index) => (
              <motion.div
                key={step.id}
                className="relative flex flex-col items-center"
                variants={nodeVariants}
                custom={index}
              >
                {/* Pulse ring */}
                <motion.div
                  className={`absolute w-20 h-20 rounded-full bg-gradient-to-br ${step.color} opacity-20 blur-xl`}
                  variants={pulseVariants}
                  animate="animate"
                  style={{ animationDelay: `${index * 0.5}s` }}
                />

                {/* Node */}
                <motion.div
                  className="relative z-10 w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center shadow-lg"
                  whileHover={{
                    scale: 1.1,
                    borderColor: 'rgba(99, 102, 241, 0.5)',
                    boxShadow: '0 0 30px rgba(99, 102, 241, 0.3)',
                  }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  <motion.div
                    className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${step.color} opacity-0`}
                    whileHover={{ opacity: 0.1 }}
                  />
                  <step.icon className="w-7 h-7 text-accent-400" />
                </motion.div>

                {/* Label */}
                <motion.div
                  className="mt-4 text-center"
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.3 + index * 0.15 }}
                >
                  <div className="text-sm font-semibold text-text-primary">
                    {step.label}
                  </div>
                  <div className="text-xs text-text-muted mt-1">
                    {step.sublabel}
                  </div>
                </motion.div>

                {/* Mobile arrow */}
                {index < workflowSteps.length - 1 && (
                  <motion.div
                    className="absolute -right-3 top-8 md:hidden text-accent-400"
                    initial={{ opacity: 0, x: -5 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 + index * 0.15 }}
                  >
                    <ArrowRight className="w-4 h-4" />
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>

          {/* Bottom info cards */}
          <motion.div
            className="mt-16 grid md:grid-cols-3 gap-4"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={staggerContainer}
          >
            {[
              { value: '30+', label: 'Job platforms scanned' },
              { value: '< 2min', label: 'Average processing time' },
              { value: '95%', label: 'ATS compatibility' },
            ].map((stat) => (
              <motion.div
                key={stat.label}
                className="flex items-center gap-3 p-4 rounded-xl bg-background/50 border border-border/50"
                variants={fadeInUp}
              >
                <div className="text-2xl font-bold text-accent-400">
                  {stat.value}
                </div>
                <div className="text-sm text-text-muted">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

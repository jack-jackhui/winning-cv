import { motion } from 'framer-motion'
import { Upload, Settings, Search, FileCheck } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const steps = [
  {
    number: '01',
    title: 'Upload Your CV',
    description:
      'Start by uploading your base CV. Our system analyzes your skills, experience, and career history.',
    icon: Upload,
  },
  {
    number: '02',
    title: 'Set Your Preferences',
    description:
      'Tell us what you\'re looking for: job titles, locations, salary range, and industry preferences.',
    icon: Settings,
  },
  {
    number: '03',
    title: 'We Find Matches',
    description:
      'Our AI scans multiple job platforms, scoring and ranking opportunities based on your profile.',
    icon: Search,
  },
  {
    number: '04',
    title: 'Get Tailored CVs',
    description:
      'For each matched job, we generate a customized CV optimized for that specific role.',
    icon: FileCheck,
  },
]

const stepVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      delay: i * 0.2,
      ease: [0.22, 1, 0.36, 1]
    }
  })
}

const connectorVariants = {
  hidden: { scaleX: 0 },
  visible: (i) => ({
    scaleX: 1,
    transition: {
      duration: 0.8,
      delay: 0.3 + i * 0.2,
      ease: [0.22, 1, 0.36, 1]
    }
  })
}

const numberBadgeVariants = {
  hidden: { scale: 0, rotate: -180 },
  visible: (i) => ({
    scale: 1,
    rotate: 0,
    transition: {
      duration: 0.5,
      delay: 0.2 + i * 0.2,
      type: 'spring',
      stiffness: 200
    }
  })
}

const iconVariants = {
  rest: { scale: 1, y: 0 },
  hover: { 
    scale: 1.1, 
    y: -5,
    transition: { duration: 0.3, type: 'spring', stiffness: 300 }
  }
}

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="overflow-hidden">
      <div className="container-default section-padding">
        {/* Header */}
        <motion.div 
          className="text-center max-w-2xl mx-auto mb-16 lg:mb-20"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={staggerContainer}
        >
          <motion.h2 
            className="text-3xl sm:text-4xl font-bold text-text-primary"
            variants={fadeInUp}
          >
            How it works
          </motion.h2>
          <motion.p 
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            Four simple steps to transform your job search experience.
          </motion.p>
        </motion.div>

        {/* Steps */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-6">
          {steps.map((step, index) => (
            <motion.div 
              key={step.number} 
              className="relative"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-50px' }}
              custom={index}
            >
              {/* Connector line (hidden on last item and on mobile) */}
              {index < steps.length - 1 && (
                <motion.div 
                  className="hidden lg:block absolute top-8 left-[calc(50%+40px)] w-[calc(100%-40px)] h-px bg-gradient-to-r from-accent-500 to-accent-400 origin-left"
                  variants={connectorVariants}
                  custom={index}
                />
              )}

              <motion.div 
                className="flex flex-col items-center text-center"
                variants={stepVariants}
                custom={index}
              >
                {/* Icon with number */}
                <motion.div 
                  className="relative mb-6"
                  variants={iconVariants}
                  initial="rest"
                  whileHover="hover"
                >
                  <motion.div 
                    className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center"
                    whileHover={{ 
                      borderColor: 'rgba(99, 102, 241, 0.5)',
                      boxShadow: '0 0 30px rgba(99, 102, 241, 0.2)'
                    }}
                  >
                    <step.icon className="w-7 h-7 text-accent-400" />
                  </motion.div>
                  <motion.div 
                    className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-accent-600 flex items-center justify-center"
                    variants={numberBadgeVariants}
                    custom={index}
                  >
                    <span className="text-xs font-semibold text-white">{step.number}</span>
                  </motion.div>
                </motion.div>

                {/* Content */}
                <motion.h3 
                  className="text-lg font-semibold text-text-primary mb-2"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.3 + index * 0.2 }}
                >
                  {step.title}
                </motion.h3>
                <motion.p 
                  className="text-sm text-text-secondary leading-relaxed max-w-xs"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.4 + index * 0.2 }}
                >
                  {step.description}
                </motion.p>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

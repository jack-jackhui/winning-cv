import { motion } from 'framer-motion'
import {
  Search,
  FileText,
  Target,
  Download,
  Bell,
  BarChart3,
} from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const features = [
  {
    name: 'Multi-Platform Job Search',
    description:
      'Automatically scans LinkedIn, Seek, Indeed, and more to find opportunities that match your skills and preferences.',
    icon: Search,
  },
  {
    name: 'AI-Powered CV Tailoring',
    description:
      'Our AI analyzes each job posting and customizes your CV to highlight the most relevant experience and skills.',
    icon: FileText,
  },
  {
    name: 'Smart Job Matching',
    description:
      'Advanced algorithms score each opportunity against your profile, showing you only the most promising matches.',
    icon: Target,
  },
  {
    name: 'One-Click Downloads',
    description:
      'Export your tailored CVs in PDF format, ready to submit. Keep track of all versions in your personal history.',
    icon: Download,
  },
  {
    name: 'Real-Time Notifications',
    description:
      'Get instant alerts via email, Telegram, or WeChat when new matching jobs are found.',
    icon: Bell,
  },
  {
    name: 'Application Analytics',
    description:
      'Track your job search progress with detailed insights on matches, applications, and success rates.',
    icon: BarChart3,
  },
]

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      delay: i * 0.1,
      ease: [0.22, 1, 0.36, 1]
    }
  })
}

const iconContainerVariants = {
  rest: { scale: 1, rotate: 0 },
  hover: { 
    scale: 1.1, 
    rotate: 5,
    transition: { duration: 0.3, ease: 'easeOut' }
  }
}

export default function Features() {
  return (
    <section id="features" className="bg-surface border-y border-border overflow-hidden">
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
            Everything you need to land your next role
          </motion.h2>
          <motion.p 
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            Powerful features designed to streamline your job search and maximize your chances of success.
          </motion.p>
        </motion.div>

        {/* Features grid */}
        <motion.div 
          className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={feature.name}
              className="group p-6 lg:p-8 rounded-2xl bg-background border border-border hover:border-accent-500/50 transition-colors duration-300"
              variants={cardVariants}
              custom={index}
              whileHover={{ 
                y: -8,
                boxShadow: '0 20px 40px -15px rgba(99, 102, 241, 0.15)',
                transition: { duration: 0.3 }
              }}
            >
              <motion.div 
                className="w-12 h-12 rounded-xl bg-accent-500/10 flex items-center justify-center mb-5"
                variants={iconContainerVariants}
                initial="rest"
                whileHover="hover"
              >
                <feature.icon className="w-6 h-6 text-accent-400" />
              </motion.div>
              <motion.h3 
                className="text-lg font-semibold text-text-primary mb-2"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delay: 0.2 + index * 0.1 }}
              >
                {feature.name}
              </motion.h3>
              <motion.p 
                className="text-text-secondary text-sm leading-relaxed"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delay: 0.3 + index * 0.1 }}
              >
                {feature.description}
              </motion.p>
              
              {/* Hover gradient line */}
              <motion.div
                className="mt-4 h-0.5 bg-gradient-to-r from-accent-500 to-accent-400 rounded-full origin-left"
                initial={{ scaleX: 0 }}
                whileHover={{ scaleX: 1 }}
                transition={{ duration: 0.3 }}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

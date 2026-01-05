import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles, Target, Zap } from 'lucide-react'
import { 
  fadeInUp, 
  staggerContainer, 
  scaleIn,
  float 
} from '../ui/AnimatedElements'

const statsData = [
  { value: '10k+', label: 'CVs Generated' },
  { value: '85%', label: 'Interview Rate' },
  { value: '4.9', label: 'User Rating' },
]

const featureHighlights = [
  { icon: Target, label: 'Smart Job Matching' },
  { icon: Sparkles, label: 'AI CV Generation' },
  { icon: Zap, label: 'Instant Results' },
]

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Animated background gradient */}
      <motion.div 
        className="absolute inset-0 bg-gradient-to-b from-accent-500/5 via-transparent to-transparent"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.5 }}
      />
      
      {/* Animated floating orbs */}
      <motion.div
        className="absolute top-20 left-[10%] w-72 h-72 bg-accent-500/10 rounded-full blur-3xl"
        variants={float}
        initial="initial"
        animate="animate"
      />
      <motion.div
        className="absolute bottom-20 right-[10%] w-96 h-96 bg-accent-600/5 rounded-full blur-3xl"
        variants={float}
        initial="initial"
        animate="animate"
        style={{ animationDelay: '2s' }}
      />
      
      {/* Grid pattern overlay */}
      <div 
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      />

      <div className="container-default relative">
        <div className="section-padding flex flex-col items-center text-center">
          {/* Badge */}
          <motion.div 
            className="badge-primary mb-8"
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            <motion.span
              animate={{ rotate: [0, 15, -15, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Sparkles className="w-3.5 h-3.5" />
            </motion.span>
            <span>AI-Powered CV Optimization</span>
          </motion.div>

          {/* Headline */}
          <motion.h1 
            className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold text-text-primary max-w-4xl text-balance leading-tight"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            Land your dream job with{' '}
            <motion.span 
              className="text-gradient-accent inline-block"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              tailored CVs
            </motion.span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p 
            className="mt-6 text-lg sm:text-xl text-text-secondary max-w-2xl text-balance"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            WinningCV automatically matches your profile to job opportunities and generates 
            perfectly tailored resumes that get you noticed by recruiters.
          </motion.p>

          {/* CTAs */}
          <motion.div 
            className="mt-10 flex flex-col sm:flex-row gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
            >
              <Link to="/signup" className="btn-primary text-base px-8 py-4">
                Start for free
                <motion.span
                  animate={{ x: [0, 4, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                >
                  <ArrowRight className="w-4 h-4" />
                </motion.span>
              </Link>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
            >
              <a href="#how-it-works" className="btn-secondary text-base px-8 py-4">
                See how it works
              </a>
            </motion.div>
          </motion.div>

          {/* Stats */}
          <motion.div 
            className="mt-20 grid grid-cols-3 gap-8 lg:gap-16"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            transition={{ delay: 0.7 }}
          >
            {statsData.map((stat, index) => (
              <motion.div 
                key={stat.label}
                className="text-center"
                variants={fadeInUp}
                custom={index}
              >
                <motion.div 
                  className="text-3xl lg:text-4xl font-bold text-text-primary"
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ 
                    duration: 0.5, 
                    delay: 0.8 + index * 0.1,
                    type: 'spring',
                    stiffness: 200
                  }}
                >
                  {stat.value}
                </motion.div>
                <motion.div 
                  className="mt-1 text-sm text-text-muted"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 1 + index * 0.1 }}
                >
                  {stat.label}
                </motion.div>
              </motion.div>
            ))}
          </motion.div>

          {/* Feature highlights */}
          <motion.div 
            className="mt-20 grid sm:grid-cols-3 gap-6 w-full max-w-3xl"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
          >
            {featureHighlights.map((feature, index) => (
              <motion.div
                key={feature.label}
                className="flex items-center gap-3 p-4 rounded-xl bg-surface border border-border"
                variants={scaleIn}
                whileHover={{ 
                  scale: 1.05, 
                  borderColor: 'rgba(99, 102, 241, 0.5)',
                  transition: { duration: 0.2 }
                }}
                custom={index}
              >
                <motion.div 
                  className="w-10 h-10 rounded-lg bg-accent-500/10 flex items-center justify-center"
                  whileHover={{ rotate: 5 }}
                >
                  <feature.icon className="w-5 h-5 text-accent-400" />
                </motion.div>
                <span className="text-sm text-text-secondary">{feature.label}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}

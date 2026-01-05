import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const floatingParticles = [
  { x: '10%', y: '20%', size: 4, delay: 0 },
  { x: '85%', y: '15%', size: 6, delay: 1 },
  { x: '75%', y: '75%', size: 5, delay: 2 },
  { x: '20%', y: '80%', size: 4, delay: 1.5 },
  { x: '50%', y: '10%', size: 3, delay: 0.5 },
  { x: '90%', y: '50%', size: 5, delay: 2.5 },
]

const particleVariants = {
  initial: { opacity: 0, scale: 0 },
  animate: (delay) => ({
    opacity: [0, 1, 0],
    scale: [0, 1, 0],
    transition: {
      duration: 4,
      delay,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  })
}

const pulseRingVariants = {
  initial: { scale: 1, opacity: 0.3 },
  animate: {
    scale: [1, 1.5, 2],
    opacity: [0.3, 0.15, 0],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeOut'
    }
  }
}

export default function CTA() {
  return (
    <section className="overflow-hidden">
      <div className="container-default section-padding">
        <motion.div 
          className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-accent-600 to-accent-800 p-8 sm:p-12 lg:p-16"
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Animated background pattern */}
          <motion.div 
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }}
            animate={{
              backgroundPosition: ['0px 0px', '60px 60px']
            }}
            transition={{
              duration: 20,
              repeat: Infinity,
              ease: 'linear'
            }}
          />

          {/* Floating particles */}
          {floatingParticles.map((particle, index) => (
            <motion.div
              key={index}
              className="absolute rounded-full bg-white"
              style={{
                left: particle.x,
                top: particle.y,
                width: particle.size,
                height: particle.size,
              }}
              variants={particleVariants}
              initial="initial"
              animate="animate"
              custom={particle.delay}
            />
          ))}

          {/* Glowing orb */}
          <motion.div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-white/10 blur-3xl"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.1, 0.2, 0.1]
            }}
            transition={{
              duration: 5,
              repeat: Infinity,
              ease: 'easeInOut'
            }}
          />

          {/* Pulse rings */}
          <motion.div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full border border-white/20"
            variants={pulseRingVariants}
            initial="initial"
            animate="animate"
          />
          <motion.div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full border border-white/20"
            variants={pulseRingVariants}
            initial="initial"
            animate="animate"
            transition={{ delay: 1 }}
          />

          <motion.div 
            className="relative text-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={staggerContainer}
          >
            {/* Sparkle icon */}
            <motion.div
              className="flex justify-center mb-6"
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, type: 'spring', stiffness: 200 }}
            >
              <motion.div
                animate={{ rotate: [0, 15, -15, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <Sparkles className="w-10 h-10 text-white/80" />
              </motion.div>
            </motion.div>

            <motion.h2 
              className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white max-w-2xl mx-auto text-balance"
              variants={fadeInUp}
            >
              Ready to transform your job search?
            </motion.h2>
            
            <motion.p 
              className="mt-4 text-lg text-white/80 max-w-xl mx-auto"
              variants={fadeInUp}
            >
              Join thousands of professionals who have accelerated their careers with WinningCV.
            </motion.p>
            
            <motion.div 
              className="mt-8 flex flex-col sm:flex-row gap-4 justify-center"
              variants={fadeInUp}
            >
              <motion.div
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                <Link
                  to="/signup"
                  className="btn bg-white text-accent-700 hover:bg-white/90 px-8 py-4 text-base font-semibold shadow-lg shadow-black/20"
                >
                  Get started free
                  <motion.span
                    animate={{ x: [0, 5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <ArrowRight className="w-4 h-4" />
                  </motion.span>
                </Link>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                <a
                  href="#features"
                  className="btn border border-white/30 text-white hover:bg-white/10 px-8 py-4 text-base backdrop-blur-sm"
                >
                  Learn more
                </a>
              </motion.div>
            </motion.div>
            
            <motion.p 
              className="mt-6 text-sm text-white/60"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.8 }}
            >
              No credit card required. Start optimizing your CVs today.
            </motion.p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

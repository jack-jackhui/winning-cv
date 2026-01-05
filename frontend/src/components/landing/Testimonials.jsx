import { motion } from 'framer-motion'
import { Star, Quote } from 'lucide-react'
import { fadeInUp, staggerContainer } from '../ui/AnimatedElements'

const testimonials = [
  {
    content:
      "WinningCV completely transformed my job search. I went from getting no responses to landing 3 interviews in my first week. The tailored CVs make a real difference.",
    author: 'Sarah Chen',
    role: 'Software Engineer',
    company: 'Now at Google',
  },
  {
    content:
      "The AI matching is incredibly accurate. It found opportunities I never would have discovered on my own, and the customized CVs helped me stand out from hundreds of applicants.",
    author: 'Michael Torres',
    role: 'Product Manager',
    company: 'Now at Stripe',
  },
  {
    content:
      "As someone who hates writing cover letters and tailoring resumes, this tool is a game-changer. It does all the heavy lifting while I focus on preparing for interviews.",
    author: 'Emily Watson',
    role: 'Data Scientist',
    company: 'Now at Meta',
  },
]

const cardVariants = {
  hidden: { opacity: 0, y: 50, rotateX: -15 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    rotateX: 0,
    transition: {
      duration: 0.7,
      delay: i * 0.15,
      ease: [0.22, 1, 0.36, 1]
    }
  })
}

const starVariants = {
  hidden: { opacity: 0, scale: 0, rotate: -180 },
  visible: (i) => ({
    opacity: 1,
    scale: 1,
    rotate: 0,
    transition: {
      duration: 0.3,
      delay: 0.5 + i * 0.05,
      type: 'spring',
      stiffness: 300
    }
  })
}

const quoteVariants = {
  hidden: { opacity: 0, scale: 0 },
  visible: {
    opacity: 0.1,
    scale: 1,
    transition: {
      duration: 0.5,
      ease: 'easeOut'
    }
  }
}

export default function Testimonials() {
  return (
    <section id="testimonials" className="bg-surface border-y border-border overflow-hidden">
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
            Trusted by job seekers worldwide
          </motion.h2>
          <motion.p 
            className="mt-4 text-lg text-text-secondary"
            variants={fadeInUp}
          >
            See what our users have to say about their experience with WinningCV.
          </motion.p>
        </motion.div>

        {/* Testimonials grid */}
        <motion.div 
          className="grid md:grid-cols-3 gap-6 lg:gap-8"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
        >
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={index}
              className="relative p-6 lg:p-8 rounded-2xl bg-background border border-border group"
              variants={cardVariants}
              custom={index}
              whileHover={{ 
                y: -10,
                borderColor: 'rgba(99, 102, 241, 0.3)',
                boxShadow: '0 25px 50px -15px rgba(0, 0, 0, 0.3)',
                transition: { duration: 0.3 }
              }}
              style={{ perspective: '1000px' }}
            >
              {/* Quote icon background */}
              <motion.div
                className="absolute top-4 right-4"
                variants={quoteVariants}
              >
                <Quote className="w-12 h-12 text-accent-400" />
              </motion.div>

              {/* Stars */}
              <div className="flex gap-1 mb-4">
                {[...Array(5)].map((_, i) => (
                  <motion.div
                    key={i}
                    variants={starVariants}
                    custom={i}
                    whileHover={{ scale: 1.2, rotate: 15 }}
                  >
                    <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                  </motion.div>
                ))}
              </div>

              {/* Quote */}
              <motion.blockquote 
                className="text-text-secondary leading-relaxed mb-6 relative z-10"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 + index * 0.15 }}
              >
                &ldquo;{testimonial.content}&rdquo;
              </motion.blockquote>

              {/* Author */}
              <motion.div 
                className="flex items-center gap-3"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4 + index * 0.15 }}
              >
                <motion.div 
                  className="w-10 h-10 rounded-full bg-accent-500/20 flex items-center justify-center"
                  whileHover={{ 
                    scale: 1.1,
                    backgroundColor: 'rgba(99, 102, 241, 0.3)'
                  }}
                >
                  <span className="text-sm font-medium text-accent-400">
                    {testimonial.author.split(' ').map(n => n[0]).join('')}
                  </span>
                </motion.div>
                <div>
                  <motion.div 
                    className="text-sm font-medium text-text-primary"
                    whileHover={{ color: '#818cf8' }}
                  >
                    {testimonial.author}
                  </motion.div>
                  <div className="text-xs text-text-muted">
                    {testimonial.role} &middot; {testimonial.company}
                  </div>
                </div>
              </motion.div>

              {/* Hover gradient overlay */}
              <motion.div
                className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent-500/5 to-transparent opacity-0 pointer-events-none"
                whileHover={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

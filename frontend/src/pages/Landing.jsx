import Hero from '../components/landing/Hero'
import Features from '../components/landing/Features'
import HowItWorks from '../components/landing/HowItWorks'
import WorkflowDiagram from '../components/landing/WorkflowDiagram'
import TypewriterDemo from '../components/landing/TypewriterDemo'
import ComparisonChart from '../components/landing/ComparisonChart'
import Testimonials from '../components/landing/Testimonials'
import CTA from '../components/landing/CTA'

export default function Landing() {
  return (
    <>
      <Hero />
      <Features />
      <WorkflowDiagram />
      <TypewriterDemo />
      <HowItWorks />
      <ComparisonChart />
      <Testimonials />
      <CTA />
    </>
  )
}

import { Link } from 'react-router-dom'
import { ArrowLeft, FileText, CheckCircle, CreditCard, ShieldAlert, Copyright, AlertTriangle, Scale, XCircle, Globe, RefreshCw, Mail } from 'lucide-react'

const sections = [
  {
    icon: CheckCircle,
    title: '1. Acceptance of Terms',
    content: (
      <>
        <p className="mb-4">
          By accessing or using WinningCV (&quot;the Service&quot;), you agree to be bound by these Terms of Service (&quot;Terms&quot;).
          If you disagree with any part of these terms, you may not access the Service.
        </p>
        <p className="mb-4">
          These Terms apply to all visitors, users, and others who access or use the Service. By using WinningCV,
          you represent that you are at least 18 years old, or that you have the legal capacity to enter into
          binding agreements in your jurisdiction.
        </p>
        <p>
          You are responsible for ensuring that your use of the Service complies with all applicable laws and
          regulations in your jurisdiction.
        </p>
      </>
    ),
  },
  {
    icon: FileText,
    title: '2. Description of Service',
    content: (
      <>
        <p className="mb-4">
          WinningCV provides an AI-powered platform for job seekers to optimize their job search. Our services include:
        </p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>Automated job scraping from multiple platforms (LinkedIn, Seek, Indeed, etc.)</li>
          <li>AI-powered job matching based on your CV and preferences</li>
          <li>Tailored CV generation optimized for specific job applications</li>
          <li>CV version management and analytics</li>
          <li>Application tracking and success metrics</li>
        </ul>
        <p>
          The Service is provided for personal career development purposes only. We do not guarantee employment
          outcomes or specific interview rates. AI-generated CVs should be reviewed and verified by users before submission.
        </p>
      </>
    ),
  },
  {
    icon: CheckCircle,
    title: '3. User Accounts',
    content: (
      <>
        <p className="mb-4">To use certain features of the Service, you must create an account. You agree to:</p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>Provide accurate and complete information during registration</li>
          <li>Maintain the security of your account credentials</li>
          <li>Promptly notify us of any unauthorized access</li>
          <li>Accept responsibility for all activities under your account</li>
        </ul>
        <p className="mb-4">
          Each account is for individual use only. Account sharing, selling, or transferring is prohibited.
          We reserve the right to terminate accounts that violate these Terms.
        </p>
        <p>
          You are solely responsible for the accuracy of information in your CV and profile. WinningCV is not
          liable for any misrepresentation in job applications.
        </p>
      </>
    ),
  },
  {
    icon: CreditCard,
    title: '4. Payment Terms',
    content: (
      <>
        <p className="font-medium text-text-primary mb-2">Free Tier:</p>
        <ul className="list-disc list-inside space-y-1 mb-4 text-text-muted">
          <li>Access to basic job matching and limited CV generations</li>
          <li>No payment required</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Premium Access:</p>
        <ul className="list-disc list-inside space-y-1 mb-4 text-text-muted">
          <li>Subscription-based pricing for unlimited features</li>
          <li>Payment processed securely through Stripe</li>
          <li>Full access to all CV generation and analytics features</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Refund Policy:</p>
        <ul className="list-disc list-inside space-y-1 mb-4 text-text-muted">
          <li>14-day money-back guarantee from purchase date</li>
          <li>Refund requests must be submitted via email to support@winningcv.com</li>
          <li>Refunds typically processed within 5-7 business days</li>
        </ul>
        <p className="text-text-muted">Prices are subject to change. Any price changes will not affect existing subscriptions until renewal.</p>
      </>
    ),
  },
  {
    icon: ShieldAlert,
    title: '5. Acceptable Use',
    content: (
      <>
        <p className="mb-4">
          You agree to use the Service only for lawful purposes and in accordance with these Terms. You agree NOT to:
        </p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>Upload false, misleading, or fraudulent information to your CV</li>
          <li>Use the Service for spam, phishing, or malicious activities</li>
          <li>Share, distribute, or reproduce our content without permission</li>
          <li>Use automated systems (bots, scrapers) to access the Service</li>
          <li>Attempt to gain unauthorized access to our systems</li>
          <li>Interfere with other users&apos; access to the Service</li>
          <li>Submit false information or impersonate others</li>
          <li>Use the Service for any commercial purpose without authorization</li>
          <li>Reverse engineer or attempt to extract source code</li>
        </ul>
        <p className="mt-4 font-medium text-text-primary">Violation of these terms may result in immediate account termination.</p>
      </>
    ),
  },
  {
    icon: Copyright,
    title: '6. Intellectual Property',
    content: (
      <>
        <p className="mb-4">All content on WinningCV, including but not limited to:</p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>AI algorithms and matching systems</li>
          <li>CV templates and formatting tools</li>
          <li>Software, design, and user interface</li>
          <li>Logos, trademarks, and branding</li>
        </ul>
        <p className="mb-4">Is owned by WinningCV or its licensors and protected by intellectual property laws.</p>
        <p className="mb-4">
          You are granted a limited, non-exclusive, non-transferable license to access and use the Service
          for personal, non-commercial career development purposes only.
        </p>
        <p>
          <span className="font-medium text-text-primary">Your Content:</span> You retain ownership of your CV content and
          personal information. By uploading content, you grant us a license to process it for providing our services.
        </p>
      </>
    ),
  },
  {
    icon: AlertTriangle,
    title: '7. Disclaimers',
    content: (
      <>
        <p className="mb-4 font-medium text-text-primary">THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTIES OF ANY KIND.</p>
        <p className="mb-4">We do not warrant that:</p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>The Service will be uninterrupted or error-free</li>
          <li>AI-generated CVs will guarantee interviews or employment</li>
          <li>Job matching results will be 100% accurate or complete</li>
          <li>The Service will meet your specific requirements</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Career Disclaimer:</p>
        <p className="text-text-muted">
          WinningCV is a tool to assist your job search. Success depends on many factors including your qualifications,
          experience, market conditions, and individual employer decisions. We do not guarantee any specific outcomes.
        </p>
      </>
    ),
  },
  {
    icon: Scale,
    title: '8. Limitation of Liability',
    content: (
      <>
        <p className="mb-4 font-medium text-text-primary">TO THE MAXIMUM EXTENT PERMITTED BY LAW:</p>
        <p className="mb-4">WinningCV and its directors, employees, partners, and affiliates shall not be liable for:</p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>Any indirect, incidental, special, or consequential damages</li>
          <li>Loss of job opportunities or career advancement</li>
          <li>Loss of data or business opportunities</li>
          <li>Any damages arising from your use or inability to use the Service</li>
        </ul>
        <p className="mb-4 text-text-muted">
          Our total liability for any claim arising from these Terms or your use of the Service shall not exceed
          the amount you paid to WinningCV in the 12 months preceding the claim.
        </p>
        <p className="text-text-muted">
          Some jurisdictions do not allow limitation of certain damages, so some of these limitations may not apply to you.
        </p>
      </>
    ),
  },
  {
    icon: XCircle,
    title: '9. Termination',
    content: (
      <>
        <p className="font-medium text-text-primary mb-2">Your Right to Terminate:</p>
        <p className="mb-4 text-text-muted">
          You may delete your account at any time through your account settings or by contacting support.
        </p>
        <p className="font-medium text-text-primary mb-2">Our Right to Terminate:</p>
        <p className="mb-2 text-text-muted">We may suspend or terminate your access if you:</p>
        <ul className="list-disc list-inside space-y-2 mb-4 text-text-muted">
          <li>Violate these Terms of Service</li>
          <li>Engage in fraudulent or illegal activity</li>
          <li>Abuse the Service or other users</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Effect of Termination:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>Upon termination, your right to use the Service ceases immediately</li>
          <li>We may retain certain information as required by law</li>
          <li>Provisions that by nature should survive termination will survive</li>
        </ul>
      </>
    ),
  },
  {
    icon: Globe,
    title: '10. Governing Law',
    content: (
      <>
        <p className="mb-4 text-text-muted">
          These Terms shall be governed by and construed in accordance with the laws of Victoria, Australia.
        </p>
        <p className="mb-4 text-text-muted">
          Any disputes arising from these Terms or your use of the Service shall be resolved in the courts
          of Victoria, Australia.
        </p>
        <p className="text-text-muted">
          If any provision of these Terms is found to be invalid or unenforceable, the remaining provisions
          will continue in full force and effect.
        </p>
      </>
    ),
  },
  {
    icon: RefreshCw,
    title: '11. Changes to Terms',
    content: (
      <>
        <p className="mb-4">We reserve the right to modify these Terms at any time. When we make changes:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>We will update the &quot;Last Updated&quot; date at the top</li>
          <li>For material changes, we will notify you via email or platform notification</li>
          <li>Continued use after changes constitutes acceptance of the new Terms</li>
        </ul>
        <p className="mt-4 text-text-muted">
          If you disagree with the modified Terms, you should discontinue use of the Service.
        </p>
      </>
    ),
  },
]

export default function Terms() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-surface border-b border-border">
        <div className="container-default py-12 lg:py-16">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 bg-accent-600/10 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-accent-500" />
            </div>
            <h1 className="text-3xl lg:text-4xl font-bold text-text-primary">Terms of Service</h1>
          </div>
          <p className="text-text-muted">Last updated: January 7, 2026</p>
        </div>
      </div>

      {/* Introduction */}
      <div className="container-default py-8">
        <p className="text-text-secondary text-lg leading-relaxed max-w-4xl">
          Welcome to WinningCV. These Terms of Service (&quot;Terms&quot;) govern your access to and use of our
          AI-powered CV tailoring and job matching platform, including our website, applications, and all
          related services. Please read these Terms carefully before using WinningCV.
        </p>
      </div>

      {/* Sections */}
      <div className="container-default pb-16">
        <div className="space-y-8">
          {sections.map((section, index) => (
            <div
              key={index}
              className="bg-surface border border-border rounded-xl p-6 lg:p-8"
            >
              <div className="flex items-start gap-4 mb-4">
                <div className="w-10 h-10 bg-accent-600/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <section.icon className="w-5 h-5 text-accent-500" />
                </div>
                <h2 className="text-xl font-semibold text-text-primary">{section.title}</h2>
              </div>
              <div className="text-text-secondary leading-relaxed pl-14">
                {section.content}
              </div>
            </div>
          ))}
        </div>

        {/* Contact Section */}
        <div className="mt-12 bg-accent-600/5 border border-accent-600/20 rounded-xl p-8 text-center">
          <h2 className="text-xl font-semibold text-text-primary mb-4">Questions About These Terms?</h2>
          <p className="text-text-muted mb-6">
            If you have any questions about these Terms of Service, please contact us:
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 text-text-secondary">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-accent-500" />
              <a href="mailto:support@winningcv.com" className="text-accent-500 hover:text-accent-400">
                support@winningcv.com
              </a>
            </div>
            <span className="hidden sm:inline text-text-muted">|</span>
            <div>Melbourne, Victoria, Australia</div>
          </div>
        </div>
      </div>
    </div>
  )
}

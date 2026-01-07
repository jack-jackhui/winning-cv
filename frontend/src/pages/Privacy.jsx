import { Link } from 'react-router-dom'
import { ArrowLeft, Shield, Eye, Lock, Users, Cookie, Database, Globe, Bell, Mail } from 'lucide-react'

const sections = [
  {
    icon: Eye,
    title: '1. Information We Collect',
    content: (
      <>
        <p className="mb-4">We collect information to provide and improve our services. This includes:</p>
        <p className="font-medium text-text-primary mb-2">Personal Information:</p>
        <ul className="list-disc list-inside space-y-1 mb-4 text-text-muted">
          <li>Name and email address when you create an account</li>
          <li>Payment information when you purchase Premium (processed securely by Stripe)</li>
          <li>Profile information you choose to provide</li>
          <li>CV/resume documents you upload for analysis</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Usage Information:</p>
        <ul className="list-disc list-inside space-y-1 mb-4 text-text-muted">
          <li>Job matching results and preferences</li>
          <li>CV generation history and analytics</li>
          <li>Time spent on different features</li>
          <li>Application progress and success metrics</li>
        </ul>
        <p className="font-medium text-text-primary mb-2">Technical Information:</p>
        <ul className="list-disc list-inside space-y-1 text-text-muted">
          <li>Device type and browser information</li>
          <li>IP address and general location</li>
          <li>Cookies and similar technologies</li>
        </ul>
      </>
    ),
  },
  {
    icon: Shield,
    title: '2. How We Use Your Information',
    content: (
      <>
        <p className="mb-4">We use collected information to:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>Provide and maintain our CV tailoring and job matching services</li>
          <li>Generate personalized CVs based on job requirements</li>
          <li>Analyze job postings and match them to your profile</li>
          <li>Track your application success and provide analytics</li>
          <li>Process payments and manage subscriptions</li>
          <li>Send important updates about our services</li>
          <li>Improve our AI algorithms and platform features</li>
          <li>Respond to customer support requests</li>
          <li>Ensure platform security and prevent fraud</li>
        </ul>
        <p className="mt-4 font-medium text-text-primary">We never sell your personal information to third parties.</p>
      </>
    ),
  },
  {
    icon: Lock,
    title: '3. Data Protection & Security',
    content: (
      <>
        <p className="mb-4">We implement industry-standard security measures:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li><span className="text-text-primary font-medium">Encryption:</span> All data is encrypted in transit (TLS/SSL) and at rest</li>
          <li><span className="text-text-primary font-medium">Secure Payments:</span> Payment processing through PCI-compliant Stripe</li>
          <li><span className="text-text-primary font-medium">Access Controls:</span> Strict access limitations to personal data</li>
          <li><span className="text-text-primary font-medium">Regular Audits:</span> Security assessments and vulnerability testing</li>
          <li><span className="text-text-primary font-medium">Data Minimization:</span> We only collect data necessary for our services</li>
          <li><span className="text-text-primary font-medium">Secure Storage:</span> Your CV documents are stored in encrypted cloud storage</li>
        </ul>
        <p className="mt-4 text-text-muted">While we strive to protect your information, no method of transmission over the Internet is 100% secure.</p>
      </>
    ),
  },
  {
    icon: Users,
    title: '4. Information Sharing',
    content: (
      <>
        <p className="mb-4">We may share information with:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li><span className="text-text-primary font-medium">Service Providers:</span> Third parties that help us operate (hosting, analytics, payment processing, AI services)</li>
          <li><span className="text-text-primary font-medium">Legal Requirements:</span> When required by law or to protect rights and safety</li>
          <li><span className="text-text-primary font-medium">Business Transfers:</span> In case of merger, acquisition, or sale of assets</li>
        </ul>
        <p className="mt-4 text-text-muted">We require all third parties to respect your privacy and handle data securely. Your CV content is never shared with employers without your explicit consent.</p>
      </>
    ),
  },
  {
    icon: Shield,
    title: '5. Your Privacy Rights',
    content: (
      <>
        <p className="mb-4">You have the right to:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li><span className="text-text-primary font-medium">Access:</span> Request a copy of your personal data</li>
          <li><span className="text-text-primary font-medium">Correction:</span> Update or correct inaccurate information</li>
          <li><span className="text-text-primary font-medium">Deletion:</span> Request deletion of your account and data</li>
          <li><span className="text-text-primary font-medium">Portability:</span> Receive your data in a portable format</li>
          <li><span className="text-text-primary font-medium">Opt-out:</span> Unsubscribe from marketing communications</li>
          <li><span className="text-text-primary font-medium">Restriction:</span> Limit how we process your data</li>
        </ul>
        <p className="mt-4 text-text-muted">To exercise these rights, contact us at <a href="mailto:support@winningcv.com" className="text-accent-500 hover:text-accent-400">support@winningcv.com</a></p>
      </>
    ),
  },
  {
    icon: Cookie,
    title: '6. Cookies & Tracking',
    content: (
      <>
        <p className="mb-4">We use cookies and similar technologies for:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li><span className="text-text-primary font-medium">Essential Cookies:</span> Required for platform functionality and authentication</li>
          <li><span className="text-text-primary font-medium">Analytics Cookies:</span> Understanding how users interact with our platform</li>
          <li><span className="text-text-primary font-medium">Preference Cookies:</span> Remembering your settings and preferences</li>
        </ul>
        <p className="mt-4 text-text-muted">You can control cookies through your browser settings. Disabling certain cookies may affect platform functionality.</p>
      </>
    ),
  },
  {
    icon: Database,
    title: '7. Data Retention',
    content: (
      <>
        <p className="mb-4">We retain your information:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li><span className="text-text-primary font-medium">Account Data:</span> Until you delete your account</li>
          <li><span className="text-text-primary font-medium">CV Documents:</span> For the duration of your account, with version history</li>
          <li><span className="text-text-primary font-medium">Job Matching History:</span> For analytics and improvement purposes</li>
          <li><span className="text-text-primary font-medium">Payment Records:</span> As required by law (typically 7 years)</li>
          <li><span className="text-text-primary font-medium">Support Communications:</span> Up to 3 years after resolution</li>
        </ul>
        <p className="mt-4 text-text-muted">Upon account deletion, we remove or anonymize your personal data within 30 days, except where retention is required by law.</p>
      </>
    ),
  },
  {
    icon: Globe,
    title: '8. International Data Transfers',
    content: (
      <>
        <p className="mb-4">Your information may be transferred to and processed in countries outside Australia:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>Our servers are primarily located in Australia</li>
          <li>Some service providers may process data in other countries</li>
          <li>We ensure appropriate safeguards are in place for international transfers</li>
        </ul>
        <p className="mt-4 text-text-muted">By using WinningCV, you consent to such transfers.</p>
      </>
    ),
  },
  {
    icon: Bell,
    title: '9. Changes to This Policy',
    content: (
      <>
        <p className="mb-4">We may update this Privacy Policy periodically:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted">
          <li>We&apos;ll notify you of significant changes via email or platform notification</li>
          <li>The &quot;Last Updated&quot; date at the top reflects the most recent revision</li>
          <li>Continued use after changes constitutes acceptance of the updated policy</li>
        </ul>
        <p className="mt-4 text-text-muted">We encourage you to review this policy regularly.</p>
      </>
    ),
  },
]

export default function Privacy() {
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
              <Shield className="w-6 h-6 text-accent-500" />
            </div>
            <h1 className="text-3xl lg:text-4xl font-bold text-text-primary">Privacy Policy</h1>
          </div>
          <p className="text-text-muted">Last updated: January 7, 2026</p>
        </div>
      </div>

      {/* Introduction */}
      <div className="container-default py-8">
        <p className="text-text-secondary text-lg leading-relaxed max-w-4xl">
          At WinningCV, we are committed to protecting your privacy. This Privacy Policy explains how we collect,
          use, disclose, and safeguard your information when you use our AI-powered CV tailoring and job matching
          platform. Please read this policy carefully. By using WinningCV, you agree to the practices described herein.
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
          <h2 className="text-xl font-semibold text-text-primary mb-4">Contact Us About Privacy</h2>
          <p className="text-text-muted mb-6">
            If you have questions about this Privacy Policy or want to exercise your privacy rights:
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

import { Outlet } from 'react-router-dom'
import Header from './Header'
import Footer from './Footer'

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 pt-16 lg:pt-20">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

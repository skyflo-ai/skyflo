import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-gray-900/80 backdrop-blur-sm">
      <nav className="container mx-auto px-6 py-4 flex justify-between items-center">
        <Link href="/" className="text-2xl font-bold text-blue-500">
          Skyflo.ai
        </Link>
        <div className="hidden md:flex space-x-6">
          <Link href="#how-it-works" className="hover:text-blue-400 transition-colors">How It Works</Link>
          <Link href="#benefits" className="hover:text-blue-400 transition-colors">Benefits</Link>
          <Link href="#pricing" className="hover:text-blue-400 transition-colors">Pricing</Link>
        </div>
        <Button variant="outline" className="hidden md:inline-flex">
          Start Free Trial
        </Button>
      </nav>
    </header>
  )
}


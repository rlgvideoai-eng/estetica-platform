import { useEffect, useState } from 'react'
import { Header } from './components/Header'
import { Hero } from './components/Hero'
import { Services } from './components/Services'
import { Gallery } from './components/Gallery'
import { Pricing } from './components/Pricing'
import { LocationHours } from './components/LocationHours'
import { Contact } from './components/Contact'
import { FAQ } from './components/FAQ'
import { Footer } from './components/Footer'
import { ChatButton } from './components/ChatButton'
import type { ContentData } from './types/content'

function App() {
  const [content, setContent] = useState<ContentData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/content.json')
      .then(res => res.json())
      .then(data => {
        setContent(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Cargando Ayudio...</p>
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Error al cargar el contenido</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <Header business={content.business} />
      <main>
        <Hero business={content.business} />
        <Services services={content.services} />
        <Gallery images={content.gallery} />
        <Pricing services={content.services} />
        <LocationHours business={content.business} />
        <Contact business={content.business} />
        <FAQ faqs={content.faqs} />
      </main>
      <Footer business={content.business} />
      <ChatButton botUsername={import.meta.env.VITE_BOT_USERNAME || 'ayudio'} />
    </div>
  )
}

export default App
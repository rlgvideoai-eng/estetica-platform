import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

// Mock fetch para content.json
global.fetch = vi.fn()

describe('App', () => {
  const mockContent = {
    business: {
      name: 'Ayudio',
      tagline: 'Tu centro de estética de confianza',
      description: 'Descripción de prueba',
      phone: '+56 2 2233 4455',
      email: 'hola@ayudio.cl',
      address: 'Av. Providencia 1234',
      instagram: 'https://instagram.com/ayudio_cl',
      mapsUrl: 'https://maps.app.goo.gl/ejemplo',
      hours: {
        weekdays: 'Lunes a Viernes: 09:00 - 19:00',
        saturday: 'Sábado: 09:00 - 14:00',
        sunday: 'Domingo: Cerrado'
      }
    },
    services: [
      {
        id: 'masajes',
        name: 'Masajes',
        icon: '💆‍♀️',
        description: 'Masajes relajantes',
        items: [
          { name: 'Masaje Relajante 60 min', price: 35000, duration: 60 }
        ]
      }
    ],
    faqs: [
      { question: '¿Cómo agendo?', answer: 'Por el bot de Telegram' }
    ],
    gallery: ['/images/test.jpg']
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockContent)
    })
  })

  it('renders loading state initially', () => {
    render(<App />)
    expect(screen.getByText('Cargando Ayudio...')).toBeInTheDocument()
  })

  it('renders business name after loading', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Ayudio')).toBeInTheDocument()
    })
  })

  it('renders chat button with correct link', async () => {
    render(<App />)
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /agenda tu hora por chat/i })
      expect(link).toHaveAttribute('href', 'https://t.me/ayudio?start=landing')
      expect(link).toHaveAttribute('target', '_blank')
    })
  })

  it('renders services section', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Masajes')).toBeInTheDocument()
      expect(screen.getByText('$35.000')).toBeInTheDocument()
    })
  })
})
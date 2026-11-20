import { useState, useEffect } from 'react'

interface ChatButtonProps {
  botUsername: string
}

export function ChatButton({ botUsername }: ChatButtonProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY
      // Ocultar al hacer scroll down, mostrar al hacer scroll up
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)
      } else {
        setIsVisible(true)
      }
      setLastScrollY(currentScrollY)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lastScrollY])

  if (!isVisible) return null

  return (
    <a
      href={`https://t.me/${botUsername}?start=landing`}
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-6 right-6 z-50 btn-primary shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 animate-bounce-subtle"
      aria-label="Agenda tu hora por chat en Telegram"
      data-testid="chat-button"
    >
      <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.487.537.133.756-.292.756-.542 0-.264-.011-1.189-.014-2.125-2.782.526-3.639-1.169-3.639-1.169-.454-1.148-1.11-1.454-1.11-1.454-.837-.563.062-.553.062-.553 1.017.072 1.532 1.02 1.532 1.02.902 1.512 2.348 1.073 2.913.823.092-.636.35-1.068.636-1.314-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.272.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.375.203 2.394.101 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .25.22.572.754.542C19.137 20.166 22 16.42 22 12c0-5.523-4.477-10-10-10z"/>
      </svg>
      <span className="hidden sm:inline">Agenda tu hora</span>
      <span className="sr-only">Abrir chat de Telegram para agendar</span>
    </a>
  )
}

// Agregar animación sutil al index.css global
// @keyframes bounce-subtle {
//   0%, 100% { transform: translateY(0); }
//   50% { transform: translateY(-4px); }
// }
// .animate-bounce-subtle { animation: bounce-subtle 3s ease-in-out infinite; }
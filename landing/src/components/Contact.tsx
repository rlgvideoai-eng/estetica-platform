import { BusinessInfo } from '../types/content'

interface ContactProps {
  business: BusinessInfo
}

export function Contact({ business }: ContactProps) {
  return (
    <section id="contacto" className="bg-white" aria-labelledby="contacto-title">
      <div className="section-container">
        <h2 id="contacto-title" className="section-title">Contáctanos</h2>
        <p className="section-subtitle">
          ¿Tienes dudas? Escríbenos por el canal que prefieras. Te responderemos a la brevedad.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          <div className="space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email
              </h3>
              <a href={`mailto:${business.email}`} className="text-primary-600 hover:text-primary-700 font-medium transition-colors">
                {business.email}
              </a>
              <p className="text-sm text-gray-500 mt-2">Respondemos en menos de 24 horas hábiles</p>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg className="w-6 h-6 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
                Teléfono
              </h3>
              <a href={`tel:${business.phone.replace(/\s/g, '')}`} className="text-primary-600 hover:text-primary-700 font-medium transition-colors">
                {business.phone}
              </a>
              <p className="text-sm text-gray-500 mt-2">Horario de atención telefónica: Lunes a Viernes 9:00-18:00</p>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg className="w-6 h-6 text-primary-500" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-3.584-.069-4.849-.149-3.225-1.664-4.771-4.919-4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-3.584-.069-4.849-.149-3.225-1.664-4.771-4.919-4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-3.584-.069-4.849-.149-3.225-1.664-4.771-4.919-4.919-1.266.058-1.644.07-4.85.07zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.849.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
                Instagram
              </h3>
              <a href={business.instagram} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:text-primary-700 font-medium transition-colors">
                @{business.instagram.split('/').pop()}
              </a>
              <p className="text-sm text-gray-500 mt-2">Síguenos para novedades, tips y promociones</p>
            </div>
          </div>

          <div className="card">
            <h3 className="text-xl font-bold text-gray-900 mb-6">¿Prefieres chatear?</h3>
            <p className="text-gray-600 mb-6">
              La forma más rápida: nuestro bot <strong>Ayudio</strong> en Telegram. Disponible 24/7, responde al instante y puedes agendar tu hora sin esperar.
            </p>
            <a
              href={`https://t.me/${import.meta.env.VITE_BOT_USERNAME || 'ayudio'}?start=landing`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary w-full sm:w-auto"
            >
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.487.537.133.756-.292.756-.542 0-.264-.011-1.189-.014-2.125-2.782.526-3.639-1.169-3.639-1.169-.454-1.148-1.11-1.454-1.11-1.454-.837-.563.062-.553.062-.553 1.017.072 1.532 1.02 1.532 1.02.902 1.512 2.348 1.073 2.913.823.092-.636.35-1.068.636-1.314-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.272.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.375.203 2.394.101 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .25.22.572.754.542C19.137 20.166 22 16.42 22 12c0-5.523-4.477-10-10-10z"/>
              </svg>
              Abrir chat en Telegram
            </a>

            <div className="mt-6 p-4 bg-gray-50 rounded-xl">
              <p className="text-sm text-gray-700">
                <strong>💬 También puedes:</strong>
              </p>
              <ul className="mt-3 space-y-2 text-sm text-gray-600">
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Preguntar por servicios y precios
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Ver disponibilidad en tiempo real
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Reservar, reprogramar o cancelar
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Hablar con una persona si lo necesitas
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
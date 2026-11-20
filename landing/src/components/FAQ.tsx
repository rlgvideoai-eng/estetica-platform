import { useState } from 'react'
import { FAQItem } from '../types/content'

interface FAQProps {
  faqs: FAQItem[]
}

export function FAQ({ faqs }: FAQProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  const toggleFaq = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <section className="bg-gray-50" aria-labelledby="faq-title">
      <div className="section-container">
        <h2 id="faq-title" className="section-title">Preguntas Frecuentes</h2>
        <p className="section-subtitle">
          Resolvemos tus dudas más comunes. Si no encuentras tu respuesta, ¡escríbenos por el chat!
        </p>

        <div className="max-w-3xl mx-auto">
          <dl className="space-y-4" role="list">
            {faqs.map((faq, index) => (
              <div key={index} className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full px-6 py-5 text-left flex items-center justify-between gap-4 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset"
                  aria-expanded={openIndex === index}
                  aria-controls={`faq-answer-${index}`}
                >
                  <dt className="font-semibold text-gray-900 pr-8 text-balance">
                    {faq.question}
                  </dt>
                  <svg
                    className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${openIndex === index ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <dd
                  id={`faq-answer-${index}`}
                  role="region"
                  aria-hidden={openIndex !== index}
                  className={`overflow-hidden transition-all duration-300 ${openIndex === index ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}
                >
                  <div className="px-6 pb-5 text-gray-600 leading-relaxed">
                    {faq.answer}
                  </div>
                </dd>
              </div>
            ))}
          </dl>

          <div className="mt-10 text-center">
            <p className="text-gray-600 mb-4">¿No encontraste tu respuesta?</p>
            <a
              href={`https://t.me/${import.meta.env.VITE_BOT_USERNAME || 'ayudio'}?start=faq`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary"
            >
              Preguntar al bot
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
import { ServiceCategory } from '../types/content'

interface ServicesProps {
  services: ServiceCategory[]
}

export function Services({ services }: ServicesProps) {
  return (
    <section id="servicios" className="bg-white" aria-labelledby="servicios-title">
      <div className="section-container">
        <h2 id="servicios-title" className="section-title">Nuestros Servicios</h2>
        <p className="section-subtitle">
          Especialistas en belleza y bienestar femenino. Todos nuestros servicios son realizados por profesionales certificadas con productos de alta calidad.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((category) => (
            <article key={category.id} className="card group">
              <div className="flex items-center gap-4 mb-4">
                <span className="text-4xl" aria-hidden="true">{category.icon}</span>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{category.name}</h3>
                  <p className="text-gray-600 text-sm">{category.description}</p>
                </div>
              </div>
              <ul className="space-y-3" role="list">
                {category.items.map((item, index) => (
                  <li key={`${category.id}-${index}`} className="flex items-center justify-between py-2 border-t border-gray-100 last:border-b-0 group-hover:bg-gray-50 rounded-lg px-3 -mx-3 transition-colors">
                    <div className="flex flex-col">
                      <span className="font-medium text-gray-900">{item.name}</span>
                      <span className="text-sm text-gray-500">{item.duration} min</span>
                    </div>
                    <span className="font-semibold text-primary-600 text-lg">
                      ${item.price.toLocaleString('es-CL')}
                    </span>
                  </li>
                ))}
              </ul>
              <a
                href={`https://t.me/${import.meta.env.VITE_BOT_USERNAME || 'ayudio'}?start=service_${category.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary w-full mt-6 text-center"
              >
                Agendar {category.name}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
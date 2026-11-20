import { ServiceCategory } from '../types/content'

interface PricingProps {
  services: ServiceCategory[]
}

export function Pricing({ services }: PricingProps) {
  // Aplanar todos los servicios para la tabla de precios
  const allItems = services.flatMap(category =>
    category.items.map(item => ({
      ...item,
      category: category.name,
      categoryIcon: category.icon
    }))
  )

  return (
    <section id="precios" className="bg-white" aria-labelledby="precios-title">
      <div className="section-container">
        <h2 id="precios-title" className="section-title">Precios Referenciales</h2>
        <p className="section-subtitle">
          Todos los precios en pesos chilenos (CLP) e incluyen IVA. Los valores son referenciales y pueden variar según la complejidad del servicio.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left" role="table">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-3 font-semibold text-gray-900">Servicio</th>
                <th className="pb-3 font-semibold text-gray-900 text-center">Duración</th>
                <th className="pb-3 font-semibold text-gray-900 text-right">Precio</th>
              </tr>
            </thead>
            <tbody>
              {services.map((category) => (
                <tbody key={category.id} className="divide-y divide-gray-100">
                  <tr>
                    <td className="py-4 font-medium text-gray-900" colSpan={3}>
                      <span className="flex items-center gap-2">
                        <span aria-hidden="true">{category.icon}</span>
                        {category.name}
                      </span>
                    </td>
                  </tr>
                  {category.items.map((item, index) => (
                    <tr key={`${category.id}-${index}`} className="hover:bg-gray-50 transition-colors">
                      <td className="py-3 text-gray-700">
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{category.categoryIcon}</span>
                          <span>{item.name}</span>
                        </div>
                      </td>
                      <td className="py-3 text-center text-gray-500">{item.duration} min</td>
                      <td className="py-3 text-right font-semibold text-primary-600">
                        ${item.price.toLocaleString('es-CL')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 p-6 bg-primary-50 rounded-2xl">
          <h3 className="text-lg font-semibold text-primary-900 mb-2">¿Necesitas un paquete personalizado?</h3>
          <p className="text-primary-700 mb-4">
            Combinamos servicios para novias, eventos especiales o rutinas de belleza completas. ¡Escríbenos y armamos tu pack ideal!
          </p>
          <a
            href={`https://t.me/${import.meta.env.VITE_BOT_USERNAME || 'ayudio'}?start=pack_personalizado`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary"
          >
            Solicitar cotización
          </a>
        </div>
      </div>
    </section>
  )
}
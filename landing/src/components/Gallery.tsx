interface GalleryProps {
  images: string[]
}

export function Gallery({ images }: GalleryProps) {
  return (
    <section id="galeria" className="bg-gray-50" aria-labelledby="galeria-title">
      <div className="section-container">
        <h2 id="galeria-title" className="section-title">Nuestra Galería</h2>
        <p className="section-subtitle">
          Un vistazo a nuestro espacio, diseñados para que te sientas cómoda y relajada desde el primer momento.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {images.map((image, index) => (
            <figure
              key={index}
              className={`group relative overflow-hidden rounded-2xl aspect-square ${
                index === 0 ? 'lg:col-span-3 lg:row-span-2' :
                index === 1 ? 'lg:col-span-3' :
                index < 4 ? 'md:col-span-2' : 'col-span-1'
              }`}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary-100 to-secondary-100" aria-hidden="true" />
              <img
                src={image}
                alt={`Ayudio - Espacio ${index + 1}`}
                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                loading={index < 4 ? 'eager' : 'lazy'}
              />
              <figcaption className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/70 to-transparent text-white text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                Ayudio - Espacio {index + 1}
              </figcaption>
            </figure>
          ))}
        </div>

        <div className="mt-10 text-center">
          <a
            href={`https://t.me/${import.meta.env.VITE_BOT_USERNAME || 'ayudio'}?start=landing`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary"
          >
            ¿Te gustó? Agenda tu visita
          </a>
        </div>
      </div>
    </section>
  )
}
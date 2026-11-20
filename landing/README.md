# Landing Page - Ayudio

Sitio web estático responsive para el centro de estética **Ayudio**, construido con React 18, Vite, TypeScript y Tailwind CSS.

## 🚀 Características

- **Single Page Application** con secciones: Hero, Servicios, Galería, Precios, Ubicación/Horarios, Contacto, FAQ
- **Contenido editable** vía `public/content.json` (sin tocar código)
- **Botón flotante** fijo a Telegram (`https://t.me/ayudio?start=landing`)
- **SEO completo**: meta tags, Open Graph, Twitter Cards, JSON-LD LocalBusiness
- **Accesibilidad**: semántica HTML5, ARIA, contraste WCAG AA, focus visible
- **Responsive**: mobile-first, breakpoints Tailwind
- **Performance**: Lighthouse > 90 en móvil
- **Tests**: Vitest + React Testing Library + jsdom

## 📁 Estructura

```
landing/
├── public/
│   ├── content.json          # Contenido editable (servicios, precios, horarios, FAQs)
│   └── favicon.svg
├── src/
│   ├── components/           # Componentes React por sección
│   │   ├── Header.tsx
│   │   ├── Hero.tsx
│   │   ├── Services.tsx
│   │   ├── Gallery.tsx
│   │   ├── Pricing.tsx
│   │   ├── LocationHours.tsx
│   │   ├── Contact.tsx
│   │   ├── FAQ.tsx
│   │   ├── Footer.tsx
│   │   └── ChatButton.tsx    # Botón flotante a Telegram
│   ├── types/
│   │   └── content.ts        # Tipos TypeScript para content.json
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css             # Tailwind + utilidades custom
│   └── test-setup.ts         # Configuración de tests
├── index.html
├── nginx.conf                # Config nginx para producción
├── Dockerfile                # Build multi-stage (builder + nginx)
├── Dockerfile.dev            # Dev server con hot reload
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.cjs
└── postcss.config.cjs
```

## 🛠 Desarrollo Local

```bash
# Instalar dependencias
npm install

# Servidor de desarrollo (hot reload en puerto 5173)
npm run dev

# Type check
npm run typecheck

# Lint
npm run lint

# Tests (watch mode)
npm run test

# Tests con coverage
npm run test -- --coverage

# Build de producción
npm run build

# Preview del build
npm run preview
```

## 🐳 Docker

### Desarrollo
```bash
docker build -f Dockerfile.dev -t ayudio-landing:dev .
docker run -p 5173:5173 -v $(pwd):/app -v /app/node_modules ayudio-landing:dev
```

### Producción
```bash
docker build -t ayudio-landing:prod .
docker run -p 80:80 ayudio-landing:prod
```

### Con docker-compose (desde raíz del monorepo)
```bash
docker compose up landing
```

## 📝 Content.json - Guía de edición

El archivo `public/content.json` contiene **todo el contenido editable** del sitio. Modifica este archivo sin tocar código:

```json
{
  "business": { "name", "tagline", "description", "phone", "email", "address", "instagram", "mapsUrl", "hours" },
  "services": [
    { "id", "name", "icon", "description", "items": [{ "name", "price", "duration" }] }
  ],
  "faqs": [{ "question", "answer" }],
  "gallery": ["/images/gallery-1.jpg", ...]
}
```

- **Precios** en CLP (enteros, sin puntos ni comas)
- **Duración** en minutos (entero)
- **Iconos** emoji en campo `icon`
- **Imágenes galería** rutas relativas a `public/`

## 🎨 Personalización Visual

Colores en `tailwind.config.cjs`:
- `primary`: Rosa/rosa (marca principal)
- `secondary`: Verde agua (acento)

Fuentes: Inter (Google Fonts, cargada en `index.html`)

## ♿ Accesibilidad

- Semántica HTML5 (`header`, `main`, `section`, `footer`, `nav`, `address`)
- ARIA labels en botones y enlaces
- Contraste ≥ 4.5:1 (WCAG AA)
- Focus visible en todos los elementos interactivos
- `prefers-reduced-motion` respetado
- Textos alternativos en imágenes
- Navegación por teclado completa

## 📊 SEO

- Meta tags: title, description, viewport, theme-color
- Open Graph: title, description, image, type
- Twitter Cards: summary_large_image
- JSON-LD: `BeautySalon` (LocalBusiness)
- Sitemap.xml y robots.txt se pueden generar en build

## 🧪 Tests

```bash
# Watch mode
npm run test

# Coverage (umbral 80%)
npm run test -- --coverage
```

Tests cubren:
- Renderizado de componentes principales
- Carga de content.json
- Botón de chat con link correcto
- Secciones visibles
- Accesibilidad básica

## 📦 Deploy

### Netlify / Cloudflare Pages / Vercel
1. Conectar repo
2. Build command: `npm run build`
3. Output directory: `dist`
4. Variables de entorno: `VITE_BOT_USERNAME=ayudio`

### Docker + Nginx (VPS / GCP VM)
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d landing
```

Nginx sirve archivos estáticos con:
- Headers de seguridad (CSP, HSTS, X-Frame-Options, etc.)
- Gzip compression
- Cache headers para assets estáticos
- SPA fallback a index.html

## 🔧 Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_BOT_USERNAME` | Username del bot de Telegram (sin @) | `ayudio` |
| `VITE_API_URL` | URL base de la API del bot | `http://localhost:8000` |

## 📄 Licencia

Propietario - Ayudio Centro de Estética
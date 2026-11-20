# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage - Nginx
FROM nginx:alpine AS production

# Copiar build de Vite
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración de nginx para SPA + headers de seguridad
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
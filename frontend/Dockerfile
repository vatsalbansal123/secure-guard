# ---- Build stage ----
FROM node:22-alpine AS build

WORKDIR /app

# Backend URL is baked into the static bundle at build time.
# Defaults to the deployed Azure backend; override with --build-arg for local builds.
ARG VITE_BACKEND_URL=https://secureguard-backend-vatsal.jollymoss-217b23fc.eastus.azurecontainerapps.io
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Serve stage ----
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# --- Stage 1: build the static assets ---
FROM node:20-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# VITE_API_BASE_URL is baked in at build time (Vite env vars are compile-time,
# not runtime) — pass it via --build-arg in CI/CD per environment.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Stage 2: serve with nginx ---
FROM nginx:1.27-alpine AS runtime

RUN apk add --no-cache curl \
    && addgroup -g 1000 razorrecon \
    && adduser -D -u 1000 -G razorrecon razorrecon

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

# nginx needs to write to these paths even running as non-root.
RUN touch /var/run/nginx.pid \
    && chown -R razorrecon:razorrecon /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html /etc/nginx/conf.d

USER razorrecon
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

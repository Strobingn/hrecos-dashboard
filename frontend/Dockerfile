# Production frontend image: static dashboard + nginx reverse proxy for /api/
# Build from the repository root so nginx.conf can be included:
#   docker build -f frontend/Dockerfile -t hrecos-frontend .
FROM nginx:alpine

# Copy the static dashboard
COPY frontend/index.html /usr/share/nginx/html/index.html

# Replace the default site config with our API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

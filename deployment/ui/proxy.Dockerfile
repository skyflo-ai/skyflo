FROM nginx:1.25-alpine


RUN apk add --no-cache curl

USER nginx

# Copy nginx configuration
COPY deployment/ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080


HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"] 
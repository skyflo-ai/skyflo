FROM nginx:1.25-alpine3.19

# Adding curl
RUN apk add --no-cache curl=8.14.1-r2

# Copy nginx configuration
COPY deployment/ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

#Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"] 
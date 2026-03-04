FROM nginxinc/nginx-unprivileged:1.25-alpine

# Copy nginx template rendered by the nginx entrypoint
COPY deployment/ui/nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"] 
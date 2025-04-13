FROM nginx:1.25-alpine

# Copy nginx configuration
COPY deployment/ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 
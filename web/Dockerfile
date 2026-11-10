FROM nginx:1.27-alpine

# Replace Nginx's default site config with ours (static files + /api proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# The dashboard files
COPY html/ /usr/share/nginx/html/

EXPOSE 80
# No CMD needed: the nginx image already starts "nginx -g 'daemon off;'"

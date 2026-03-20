FROM node:20-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build
COPY . .

# Set the backend API URL for production build
# Nginx will proxy /api to the backend
ENV VITE_API_BASE_URL=/api

RUN npm run build

# --- Production stage: serve with Nginx ---
FROM nginx:alpine

# Copy the built React app to Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

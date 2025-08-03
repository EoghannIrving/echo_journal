# Build stage for compiling CSS with Node.js
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json tailwind_src.css tailwind.config.js ./
RUN npm ci && mkdir -p static && npm run build:css && npm cache clean --force

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Copy only the built CSS artifact from the build stage
COPY --from=build /app/static/tailwind.css ./static/tailwind.css
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

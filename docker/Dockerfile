# Build stage for compiling CSS with Node.js
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json tailwind_src.css tailwind.config.js ./
RUN npm ci && mkdir -p static && npm run build:css && npm cache clean --force

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
# Copy application source and install dependencies from pyproject.toml
COPY . .
RUN pip install --no-cache-dir .
# Copy only the built CSS artifact from the build stage
COPY --from=build /app/static/tailwind.css ./static/tailwind.css
EXPOSE 8000
ENV ECHO_JOURNAL_HOST=0.0.0.0
ENV ECHO_JOURNAL_PORT=8000
CMD ["python", "-m", "echo_journal.main"]

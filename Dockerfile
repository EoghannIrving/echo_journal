FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
COPY package.json ./
COPY tailwind_src.css ./
COPY tailwind.config.js ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    npm install && npm run build:css && \
    npm cache clean --force && \
    rm -rf node_modules
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

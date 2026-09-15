FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY . .
ENV MOCK_MODE=true
CMD ["uvicorn", "centinela.main:app", "--host", "0.0.0.0", "--port", "8000"]


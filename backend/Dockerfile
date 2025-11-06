FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --frozen

COPY src ./src
COPY main.py ./

EXPOSE 7860

CMD ["uv", "run", "python", "main.py"]
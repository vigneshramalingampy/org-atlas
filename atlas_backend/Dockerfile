FROM astral-sh/uv:python3.13-alpine

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY . .

CMD ["uv", "run", "python", "-m", "atlas_backend"]

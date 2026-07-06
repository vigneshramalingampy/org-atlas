FROM astral-sh/uv:python3.11-alpine

WORKDIR /app

# Enable bytecode compilation for faster container startups
ENV UV_COMPILE_BYTECODE=1

# Copy configuration files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies exactly as specified in the lockfile
RUN uv sync --frozen --no-cache

# Copy the rest of your application code
COPY . .

# Run the module using uv run
CMD ["uv", "run", "python", "-m", "utopia"]

import uvicorn

from atlas_backend.core.settings import settings


def main() -> None:
    """Entrypoint of the Application"""
    if settings.reload:
        uvicorn.run(
            "atlas_backend.core.application:app",
            workers=4,
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            log_level=settings.log_level.value.lower(),
            factory=True,
        )


if __name__ == "__main__":
    main()
# from sentence_transformers import SentenceTransformer

# model = SentenceTransformer(
#     "Qwen/Qwen3-Embedding-0.6B",
#     trust_remote_code=True,
# )

# embedding = model.encode("Hello World")

# print(type(embedding))

# print(embedding)

from atlas_backend.provider.knowledge.vector_store.base import SearchResult


class PromptBuilder:
    SYSTEM_TEMPLATE = """You are a helpful assistant answering questions based on the provided context.

Context:
{context}

Instructions:
- Answer based only on the provided context.
- If the context doesn't contain enough information to answer, say so clearly.
- Cite the source filename and page number when possible.
- Be concise and accurate."""

    @staticmethod
    def build(query: str, results: list[SearchResult]) -> list[dict]:
        context_parts: list[str] = []
        for i, r in enumerate(results, 1):
            source = r.payload.get("source", "unknown")
            page = r.payload.get("page")
            text = r.payload.get("text", "")
            page_info = f" (page {page})" if page is not None else ""
            context_parts.append(f"[{i}] From {source}{page_info}:\n{text}")

        context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No relevant context found."
        )

        system_prompt = PromptBuilder.SYSTEM_TEMPLATE.format(context=context)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

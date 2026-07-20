from atlas_backend.provider.knowledge.graph_store.base import Subgraph
from atlas_backend.provider.knowledge.vector_store.base import SearchResult


class PromptBuilder:
    SYSTEM_TEMPLATE = """You are a helpful assistant answering questions based on the provided context.

{graph_section}
Context:
{context}

Instructions:
- Answer based only on the provided context.
- If the context doesn't contain enough information to answer, say so clearly.
- Cite the source filename and page number when possible.
- When entities and relationships are provided, use them to give more structured and connected answers.
- Be concise and accurate."""

    @staticmethod
    def build(
        query: str,
        results: list[SearchResult],
        subgraph: Subgraph | None = None,
    ) -> list[dict]:
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

        graph_section = PromptBuilder._build_graph_section(subgraph)

        system_prompt = PromptBuilder.SYSTEM_TEMPLATE.format(
            graph_section=graph_section,
            context=context,
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

    @staticmethod
    def _build_graph_section(subgraph: Subgraph | None) -> str:
        if not subgraph or not subgraph.entities:
            return ""

        lines: list[str] = ["Knowledge Graph:"]

        entity_lines: list[str] = []
        for entity in subgraph.entities:
            props = entity.properties
            doc_id = props.get("document_id", "")
            entity_lines.append(
                f"  - {entity.name} (type: {entity.entity_type})"
                + (f" [doc: {doc_id}]" if doc_id else "")
            )
        if entity_lines:
            lines.append("Entities:")
            lines.extend(entity_lines)

        if subgraph.relationships:
            lines.append("")
            lines.append("Relationships:")
            for rel in subgraph.relationships:
                lines.append(
                    f"  - [{rel.relation_type}] {rel.source_id} -> {rel.target_id}"
                )

        return "\n".join(lines) + "\n\n"

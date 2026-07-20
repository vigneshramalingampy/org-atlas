import json
from uuid import uuid4

from loguru import logger

from atlas_backend.modules.ingestion.graph.base import GraphExtractor
from atlas_backend.provider.knowledge.graph_store.base import Entity, Relationship
from atlas_backend.provider.llm.base import LLMProvider

EXTRACTION_PROMPT = """Extract all named entities and relationships from the following text.

Return ONLY valid JSON with this exact structure:
{{
  "entities": [
    {{"name": "entity name", "entity_type": "Person|Organization|Technology|Concept|Event|Location|Document"}}
  ],
  "relationships": [
    {{"source": "source entity name", "target": "target entity name", "relation_type": "relationship type (e.g. WORKS_AT, USES, PART_OF, MENTIONS, RELATED_TO)"}}
  ]
}}

Rules:
- Entity names must be exact strings from the text (case-sensitive).
- Each relationship must reference two entities that appear in the entities list.
- Extract ALL meaningful entities and relationships.
- Do NOT include a preamble or explanation, only the JSON object.

Text:
{text}"""


class LLMGraphExtractor(GraphExtractor):
    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str = "",
    ) -> None:
        self._llm = llm_provider
        self._model = model

    async def extract(
        self,
        text: str,
        chunk_id: str,
        document_id: str,
    ) -> tuple[list[Entity], list[Relationship]]:
        prompt = EXTRACTION_PROMPT.format(text=text[:4000])

        response = await self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self._model,
            temperature=0.0,
            max_tokens=2048,
        )

        parsed = self._parse_response(response)
        if parsed is None:
            return [], []

        raw_entities = parsed.get("entities", [])
        raw_relationships = parsed.get("relationships", [])

        name_to_id: dict[str, str] = {}
        entities: list[Entity] = []
        for ent in raw_entities:
            name = ent.get("name", "").strip()
            if not name:
                continue
            if name not in name_to_id:
                eid = str(uuid4())
                name_to_id[name] = eid
                entities.append(
                    Entity(
                        id=eid,
                        name=name,
                        entity_type=ent.get("entity_type", "Concept"),
                        properties={"chunk_id": chunk_id, "document_id": document_id},
                    )
                )

        relationships: list[Relationship] = []
        seen_rels: set[tuple[str, str, str]] = set()
        for rel in raw_relationships:
            source_name = rel.get("source", "").strip()
            target_name = rel.get("target", "").strip()
            rel_type = rel.get("relation_type", "RELATED_TO").upper()

            if not source_name or not target_name:
                continue
            if source_name not in name_to_id:
                continue
            if target_name not in name_to_id:
                continue

            rel_key = (source_name, target_name, rel_type)
            if rel_key in seen_rels:
                continue
            seen_rels.add(rel_key)

            relationships.append(
                Relationship(
                    id=str(uuid4()),
                    source_id=name_to_id[source_name],
                    target_id=name_to_id[target_name],
                    relation_type=rel_type,
                    properties={"chunk_id": chunk_id, "document_id": document_id},
                )
            )

        logger.debug(
            "Extracted {} entities and {} relationships from chunk {}",
            len(entities),
            len(relationships),
            chunk_id,
        )
        return entities, relationships

    @staticmethod
    def _parse_response(response: str) -> dict | None:
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse graph extraction response")
            return None

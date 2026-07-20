from loguru import logger
from surrealdb import AsyncSurreal

from atlas_backend.provider.knowledge.graph_store.base import (
    Entity,
    GraphStore,
    Relationship,
    Subgraph,
)

ENTITIES_TABLE = "entities"
RELATIONS_TABLE = "entity_relations"


class SurrealDBGraphStore(GraphStore):
    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        user: str = "root",
        password: str = "root",
    ) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._user = user
        self._password = password
        self._client = AsyncSurreal(url)

    async def connect(self) -> None:
        await self._client.connect()
        await self._client.signin({"user": self._user, "pass": self._password})
        await self._client.use(self._namespace, self._database)
        logger.info("Connected to SurrealDB graph store at {}", self._url)

    async def initialize(self) -> None:
        await self._client.query(
            f"""
            DEFINE TABLE IF NOT EXISTS {ENTITIES_TABLE} SCHEMAFULL;
            DEFINE FIELD IF NOT EXISTS entity_id ON {ENTITIES_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS name ON {ENTITIES_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS entity_type ON {ENTITIES_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS document_id ON {ENTITIES_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS properties ON {ENTITIES_TABLE} TYPE object;
            DEFINE INDEX IF NOT EXISTS idx_entity_name ON {ENTITIES_TABLE} FIELDS name;
            DEFINE INDEX IF NOT EXISTS idx_entity_type ON {ENTITIES_TABLE} FIELDS entity_type;
            DEFINE INDEX IF NOT EXISTS idx_entity_doc ON {ENTITIES_TABLE} FIELDS document_id;

            DEFINE TABLE IF NOT EXISTS {RELATIONS_TABLE} SCHEMAFULL
                TYPE RELATION FROM {ENTITIES_TABLE} TO {ENTITIES_TABLE};
            DEFINE FIELD IF NOT EXISTS relation_type ON {RELATIONS_TABLE} TYPE string;
            DEFINE FIELD IF NOT EXISTS properties ON {RELATIONS_TABLE} TYPE object;
            """
        )
        logger.info("Initialized SurrealDB graph schema")

    async def add_entity(self, entity: Entity) -> str:
        result = await self._client.create(
            ENTITIES_TABLE,
            {
                "entity_id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
            },
        )
        if result and len(result) > 0:
            return str(result[0].get("id", entity.id))
        return entity.id

    async def add_relationship(self, relationship: Relationship) -> str:
        query = f"""
            LET $from = (SELECT id FROM {ENTITIES_TABLE} WHERE entity_id = $from_id);
            LET $to = (SELECT id FROM {ENTITIES_TABLE} WHERE entity_id = $to_id);
            RELATE $from[0]->{RELATIONS_TABLE}->$to[0]
                SET relation_type = $rel_type, properties = $props;
        """
        results = await self._client.query(
            query,
            {
                "from_id": relationship.source_id,
                "to_id": relationship.target_id,
                "rel_type": relationship.relation_type,
                "props": relationship.properties,
            },
        )
        if results and len(results) > 2:
            return str(results[2].get("id", ""))
        return relationship.id

    async def upsert_entities(self, entities: list[Entity], document_id: str) -> None:
        for entity in entities:
            existing = await self._client.query(
                f"SELECT id FROM {ENTITIES_TABLE} WHERE name = $name AND entity_type = $type",
                {"name": entity.name, "type": entity.entity_type},
            )
            if existing and len(existing) > 0:
                continue
            entity.properties["document_id"] = document_id
            await self.add_entity(entity)

    async def upsert_relationships(self, relationships: list[Relationship]) -> None:
        for rel in relationships:
            source = await self._client.query(
                f"SELECT id FROM {ENTITIES_TABLE} WHERE entity_id = $eid",
                {"eid": rel.source_id},
            )
            target = await self._client.query(
                f"SELECT id FROM {ENTITIES_TABLE} WHERE entity_id = $eid",
                {"eid": rel.target_id},
            )
            if not source or not source[0].get("id"):
                continue
            if not target or not target[0].get("id"):
                continue
            await self.add_relationship(rel)

    async def traverse(
        self,
        start_id: str,
        depth: int = 2,
        relation_types: list[str] | None = None,
    ) -> Subgraph:
        rel_filter = ""
        if relation_types:
            types = ", ".join(f"'{t}'" for t in relation_types)
            rel_filter = f"WHERE relation_type IN [{types}]"

        query = f"""
            SELECT * FROM {ENTITIES_TABLE} WHERE entity_id = $start_id;
            SELECT ->{RELATIONS_TABLE}{rel_filter}->* AS out_rels,
                   <-{RELATIONS_TABLE}{rel_filter}<-* AS in_rels
            FROM {ENTITIES_TABLE}
            WHERE entity_id = $start_id;
        """
        results = await self._client.query(query, {"start_id": start_id})

        if not results or len(results) < 2:
            return Subgraph()

        visited_entities: dict[str, dict] = {}
        visited_rels: list[dict] = []

        if results[0] and len(results[0]) > 0:
            entity = results[0][0]
            visited_entities[entity.get("entity_id", "")] = entity

        queue: list[str] = [start_id]
        current_depth = 0

        while queue and current_depth < depth:
            next_queue: list[str] = []
            for eid in queue:
                query = f"""
                    SELECT ->{RELATIONS_TABLE}{rel_filter}->* AS out_rels,
                           <-{RELATIONS_TABLE}{rel_filter}<-* AS in_rels
                    FROM {ENTITIES_TABLE}
                    WHERE entity_id = $eid;
                """
                res = await self._client.query(query, {"eid": eid})
                if not res or not res[0]:
                    continue

                for edge_dir in ["out_rels", "in_rels"]:
                    edges = res[0].get(edge_dir) or []
                    for edge in edges:
                        if not isinstance(edge, dict):
                            continue
                        in_id = edge.get("in", "")
                        out_id = edge.get("out", "")

                        visited_rels.append(edge)

                        target_id = out_id if edge_dir == "out_rels" else in_id
                        if isinstance(target_id, dict):
                            target_id = target_id.get("id", "")
                        if (
                            isinstance(target_id, str)
                            and target_id not in visited_entities
                        ):
                            next_queue.append(target_id)

            queue = next_queue
            current_depth += 1

        entity_ids = list(visited_entities.keys())
        if entity_ids:
            placeholders = ", ".join(f"'{eid}'" for eid in entity_ids)
            entity_records = await self._client.query(
                f"SELECT * FROM {ENTITIES_TABLE} WHERE entity_id IN [{placeholders}]"
            )
        else:
            entity_records = []

        entities = []
        for record in entity_records or []:
            if not isinstance(record, dict):
                continue
            entities.append(
                Entity(
                    id=record.get("entity_id", ""),
                    name=record.get("name", ""),
                    entity_type=record.get("entity_type", ""),
                    properties=record.get("properties", {}),
                )
            )

        relationships = []
        for edge in visited_rels:
            if not isinstance(edge, dict):
                continue
            out_raw = edge.get("out", "")
            in_raw = edge.get("in", "")
            out_id = (
                out_raw.get("id", "") if isinstance(out_raw, dict) else str(out_raw)
            )
            in_id = in_raw.get("id", "") if isinstance(in_raw, dict) else str(in_raw)
            relationships.append(
                Relationship(
                    id=edge.get("id", ""),
                    source_id=out_id,
                    target_id=in_id,
                    relation_type=edge.get("relation_type", ""),
                    properties=edge.get("properties", {}),
                )
            )

        return Subgraph(entities=entities, relationships=relationships)

    async def find_entity(
        self, name: str, entity_type: str | None = None
    ) -> list[Entity]:
        if entity_type:
            results = await self._client.query(
                f"SELECT * FROM {ENTITIES_TABLE} WHERE name CONTAINS $name AND entity_type = $type",
                {"name": name, "type": entity_type},
            )
        else:
            results = await self._client.query(
                f"SELECT * FROM {ENTITIES_TABLE} WHERE name CONTAINS $name",
                {"name": name},
            )

        entities = []
        for record in results or []:
            if not isinstance(record, dict):
                continue
            entities.append(
                Entity(
                    id=record.get("entity_id", ""),
                    name=record.get("name", ""),
                    entity_type=record.get("entity_type", ""),
                    properties=record.get("properties", {}),
                )
            )
        return entities

    async def find_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        relation_types: list[str] | None = None,
    ) -> list[Entity]:
        subgraph = await self.traverse(entity_id, depth, relation_types)
        return [e for e in subgraph.entities if e.id != entity_id]

    async def delete_by_document(self, document_id: str) -> None:
        entities = await self._client.query(
            f"SELECT id, entity_id FROM {ENTITIES_TABLE} WHERE document_id = $doc_id",
            {"doc_id": document_id},
        )
        if not entities:
            return
        for ent in entities:
            if not isinstance(ent, dict):
                continue
            ent_id = ent.get("entity_id", "")
            if not ent_id:
                continue
            await self._client.query(
                f"DELETE {RELATIONS_TABLE} WHERE ->{ENTITIES_TABLE}->entity_id = $eid OR <-{ENTITIES_TABLE}<-entity_id = $eid",
                {"eid": ent_id},
            )
        await self._client.query(
            f"DELETE FROM {ENTITIES_TABLE} WHERE document_id = $doc_id",
            {"doc_id": document_id},
        )

    async def close(self) -> None:
        await self._client.close()

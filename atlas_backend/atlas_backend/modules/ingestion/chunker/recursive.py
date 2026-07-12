import re
import uuid

from atlas_backend.modules.ingestion.chunker.base import TextChunker
from atlas_backend.modules.ingestion.chunker.config import ChunkingConfig
from atlas_backend.modules.ingestion.chunker.model import Chunk, ChunkMetadata
from atlas_backend.modules.ingestion.extractor.model import ParsedDocument


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_recursive(text: str, separators: list[str], max_size: int) -> list[str]:
    if _estimate_tokens(text) <= max_size:
        return [text] if text.strip() else []

    for separator in separators:
        if separator not in text:
            continue

        parts = text.split(separator)
        result: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + separator + part).strip() if current else part
            if _estimate_tokens(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    result.append(current)
                if _estimate_tokens(part) > max_size and len(separators) > 1:
                    remaining_seps = separators[separators.index(separator) + 1 :]
                    result.extend(_split_recursive(part, remaining_seps, max_size))
                    current = ""
                else:
                    current = part

        if current.strip():
            result.append(current)

        if result:
            return result

    words = text.split()
    result = []
    current_words: list[str] = []

    for word in words:
        current_words.append(word)
        if _estimate_tokens(" ".join(current_words)) >= max_size:
            result.append(" ".join(current_words))
            current_words = []

    if current_words:
        result.append(" ".join(current_words))

    return result


def _detect_section(text: str) -> str | None:
    heading_pattern = re.compile(
        r"^(#{1,6}\s+.+|"
        r"[A-Z][A-Za-z0-9 ]{2,50}\s*\n[-=]{3,}|"
        r"[A-Z][A-Za-z0-9 ]{2,50}$)",
        re.MULTILINE,
    )
    match = heading_pattern.search(text)
    if match:
        heading = match.group(0).strip().lstrip("#").strip()
        heading = re.sub(r"\n[-=]{3,}$", "", heading)
        return heading.strip()
    return None


class RecursiveChunker(TextChunker):
    async def chunk(
        self, document: ParsedDocument, config: ChunkingConfig
    ) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        parent_chunks: list[Chunk] = []
        global_index = 0

        for page in document.pages:
            if not page.text.strip():
                continue

            macro_texts = _split_recursive(
                page.text, ["\n\n", "\n"], config.parent_size
            )

            for macro_text in macro_texts:
                if not macro_text.strip():
                    continue

                parent_id = str(uuid.uuid4())
                section = _detect_section(macro_text)
                macro_tokens = _estimate_tokens(macro_text)

                parent_chunk = Chunk(
                    id=parent_id,
                    text=macro_text,
                    index=global_index,
                    parent_id=None,
                    child_ids=[],
                    metadata=ChunkMetadata(
                        source=document.metadata.filename,
                        page=page.page_number,
                        section=section,
                        file_type=document.metadata.file_type,
                        char_count=len(macro_text),
                        token_count=macro_tokens,
                    ),
                )
                parent_chunks.append(parent_chunk)

                if macro_tokens <= config.max_chunk_size:
                    child_id = str(uuid.uuid4())
                    child_chunk = Chunk(
                        id=child_id,
                        text=macro_text,
                        index=global_index,
                        parent_id=parent_id,
                        child_ids=[],
                        metadata=ChunkMetadata(
                            source=document.metadata.filename,
                            page=page.page_number,
                            section=section,
                            file_type=document.metadata.file_type,
                            char_count=len(macro_text),
                            token_count=macro_tokens,
                        ),
                    )
                    parent_chunk.child_ids = [child_id]
                    all_chunks.append(child_chunk)
                    global_index += 1
                else:
                    micro_texts = _split_recursive(
                        macro_text, config.separators, config.max_chunk_size
                    )
                    child_ids: list[str] = []

                    for micro_text in micro_texts:
                        if not micro_text.strip():
                            continue
                        if _estimate_tokens(micro_text) < config.min_chunk_size:
                            continue

                        child_id = str(uuid.uuid4())
                        child_ids.append(child_id)
                        micro_tokens = _estimate_tokens(micro_text)

                        child_chunk = Chunk(
                            id=child_id,
                            text=micro_text,
                            index=global_index,
                            parent_id=parent_id,
                            child_ids=[],
                            metadata=ChunkMetadata(
                                source=document.metadata.filename,
                                page=page.page_number,
                                section=section,
                                file_type=document.metadata.file_type,
                                char_count=len(micro_text),
                                token_count=micro_tokens,
                            ),
                        )
                        all_chunks.append(child_chunk)
                        global_index += 1

                    parent_chunk.child_ids = child_ids

        all_chunks.extend(parent_chunks)
        return all_chunks

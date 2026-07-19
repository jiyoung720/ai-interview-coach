from rag.loader import chunk_text
from pathlib import Path

kb_dir = Path('kb')
for md_file in sorted(kb_dir.glob('*.md')):
    text = md_file.read_text(encoding='utf-8')
    chunks = chunk_text(text, source=md_file.name)
    short_chunks = [c for c in chunks if len(c.page_content) < 50]
    if short_chunks:
        print(f'{md_file.name}: {len(short_chunks)}개의 짧은 chunk 발견')
        for c in short_chunks:
            print(f'  -> {repr(c.page_content)}')

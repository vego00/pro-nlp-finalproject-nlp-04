"""Import old drafts: uv run python -m storage.import_drafts PATH [--dry-run]."""
import argparse
import asyncio
import json
import re
from pathlib import Path
from fastapi import HTTPException
from storage import repository
from storage.database import get_engine

async def main():
    from web.app import Draft, initial_state
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.dry_run:
        await repository.ensure_owner()
    paths = sorted(args.path.glob('*')) if args.path.is_dir() else [args.path]
    stems = sorted({p.with_suffix('') for p in paths if p.suffix in {'.md', '.json'}})
    for stem in stems:
        try:
            if not re.fullmatch(r'[0-9a-f]{32}', stem.name):
                raise ValueError('올바르지 않은 세션 ID')
            if stem.with_suffix('.json').exists():
                raw = json.loads(stem.with_suffix('.json').read_text())
            else:
                raw = {'markdown': stem.with_suffix('.md').read_text()}
            draft = Draft(**{**raw, 'base_revision': 0})
            try:
                await repository.get(stem.name)
                print(stem.name, '건너뜀: 기존 세션')
                continue
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise
            if not args.dry_run:
                await repository.create(initial_state(), draft.markdown, draft.document, stem.name)
            print(stem.name, '검증 완료' if args.dry_run else '가져오기 완료')
        except Exception as exc:
            print(stem.name, '실패:', type(exc).__name__)
    await get_engine().dispose()

if __name__ == '__main__':
    asyncio.run(main())

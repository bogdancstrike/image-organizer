"""Validated destinations compiled from natural-language AI sorting instructions."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date

from .planner import safe_folder

MAX_RULES = 12
_BAD = re.compile(r'[\\:*?"<>|{}\x00-\x1f\x7f]')


@dataclass(frozen=True)
class Rule:
    what: str
    folder: str
    rest: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def validate_rules(data: list[dict], today: date | None = None) -> list[Rule]:
    """Reject unsafe/ambiguous model output instead of silently changing destinations."""
    today = today or date.today()
    if not isinstance(data, list) or not 1 <= len(data) <= MAX_RULES:
        raise ValueError(f'AI must return between 1 and {MAX_RULES} prompt rules')
    rules, seen = [], set()
    for item in data:
        if not isinstance(item, dict) or set(item) != {'what', 'folder', 'rest'}:
            raise ValueError('AI returned an invalid prompt rule')
        what, folder, rest = item['what'], item['folder'], item['rest']
        if not isinstance(what, str) or len(what) > 1000 or type(rest) is not bool:
            raise ValueError('AI returned an invalid rule description')
        if not isinstance(folder, str):
            raise ValueError('AI returned an invalid destination folder')
        for token, value in {'date': today.strftime('%d.%m.%Y'), 'today': today.strftime('%d.%m.%Y'),
                             'year': today.strftime('%Y'), 'month': today.strftime('%m'), 'iso': today.isoformat()}.items():
            folder = folder.replace('{' + token + '}', value)
        parts = folder.split('/')
        if (not folder or len(folder) > 400 or _BAD.search(folder)
                or any(not p or p.startswith(('.', '~')) or p != p.strip() or p.endswith('.') or len(p) > 80 for p in parts)
                or safe_folder(folder) != folder):
            raise ValueError(f'Unsafe destination folder: {folder!r}. Use relative folders without traversal or special characters.')
        if folder.casefold() in seen:
            raise ValueError('Each prompt rule must have a distinct destination folder')
        seen.add(folder.casefold())
        if not rest and not what.strip():
            raise ValueError('Each matching rule needs a photo description')
        if rest and what.strip():
            raise ValueError('The catch-all rule must have an empty description')
        rules.append(Rule(what.strip(), folder, rest))
    if sum(r.rest for r in rules) > 1 or all(r.rest for r in rules):
        raise ValueError('Use at least one matching rule and at most one everything-else rule')
    return rules

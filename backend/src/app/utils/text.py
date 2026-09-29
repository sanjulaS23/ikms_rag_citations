import re
from typing import Iterable


CITATION_RE = re.compile(r"\[(C\d+)\]")


def extract_citation_ids(text: str) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for match in CITATION_RE.finditer(text or ""):
        cid = match.group(1)
        if cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


def remove_invalid_citations(text: str, valid_ids: Iterable[str]) -> str:
    valid = set(valid_ids)

    def _replace(match: re.Match[str]) -> str:
        cid = match.group(1)
        return match.group(0) if cid in valid else ""

    return CITATION_RE.sub(_replace, text or "")

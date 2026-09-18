"""Self-check for issue #4: the audio-language fallback must be detectable.

Run from docker/:  python -m app.core.test_episode_index
"""

from __future__ import annotations

import json
from pathlib import Path

from .episode_index import audio_lang, best_source_for

INDEX = Path(__file__).resolve().parents[2] / "data" / "episode_index.json"


def _episodes() -> list[tuple[str, dict]]:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    out: list[tuple[str, dict]] = []
    for arc in data.get("arcs", []):
        for ep in arc.get("episodes", []):
            out.append((f"{arc['title']} EP{ep['num']}", ep))
    return out


def main() -> None:
    # Language mapping
    assert audio_lang("English Subtitles") == "ja"
    assert audio_lang("English Dub") == "en"
    assert audio_lang("English Dub with Closed Captions") == "en"
    assert audio_lang("") == "en"

    eps = _episodes()
    sub_only = [
        (name, ep) for name, ep in eps
        if [s for s in ep.get("sources", []) if s.get("kind") == "onepace"]
        and not any(
            "Dub" in s.get("version", "")
            for s in ep["sources"] if s.get("kind") == "onepace"
        )
    ]
    assert sub_only, "test data: expected at least one sub-only episode"

    # Dub preferred on a sub-only episode: fallback returns Japanese audio
    # and the mismatch expression (mirrors routes_downloads.py) catches it.
    name, ep = sub_only[0]
    src = best_source_for(ep, "onepace", "English Dub", "1080p")
    assert src is not None, f"{name}: expected Japanese fallback"
    assert audio_lang(src.get("version", "")) == "ja"
    assert (
        audio_lang(src.get("version", "")) != audio_lang("English Dub")
    ), "mismatch must be flagged"

    # Same episode, Sub preferred: no mismatch.
    src = best_source_for(ep, "onepace", "English Subtitles", "1080p")
    assert src is not None
    assert audio_lang(src.get("version", "")) == "ja"
    assert audio_lang(src.get("version", "")) == audio_lang("English Subtitles")

    # Dub preferred where a dub exists: no mismatch.
    dubbed = next(
        (ep for name, ep in eps
         if any("Dub" in s.get("version", "")
                for s in ep.get("sources", [])
                if s.get("kind") == "onepace")),
        None,
    )
    assert dubbed is not None, "test data: expected at least one dubbed episode"
    src = best_source_for(dubbed, "onepace", "English Dub", "1080p")
    assert src is not None
    assert audio_lang(src.get("version", "")) == "en"
    assert audio_lang(src.get("version", "")) == audio_lang("English Dub")

    print(f"OK — checked {len(eps)} episodes "
          f"({len(sub_only)} sub-only), language fallback detected.")


if __name__ == "__main__":
    main()

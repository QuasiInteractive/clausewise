"""Answer a question from retrieved sources only, with a citation on every point.

The model sees numbered sources and must cite them as [1], [2]. If the sources don't cover the
question it must reply with the refusal marker instead of drawing on general knowledge. The
output is then checked in code: any citation number that wasn't supplied fails the answer, and
an answer with no citations at all is treated as a refusal. Code decides what reaches the user;
the model only writes (the lesson from Mule Crew).
"""

import re
from dataclasses import dataclass

import anthropic

from clausewise.config import settings
from clausewise.retrieve import Hit

NOT_COVERED = "NOT_COVERED"
NOT_COVERED_MESSAGE = (
    "The Queensland tenancy rules I have don't cover that, so I can't answer it reliably. "
    "The RTA (1300 366 311) or a tenant advocacy service can help."
)
DISCLAIMER = "General information about Queensland tenancy rules, not legal advice."

_CITATION = re.compile(r"\[(\d+)\]")

SYSTEM = f"""You explain Queensland residential tenancy rules to renters and owners in plain
English (around Year 9 reading level).

Rules:
- Use ONLY the numbered sources provided. Do not use outside knowledge, even if you are sure.
- Every sentence that states a rule must end with its source number, like [2]. Use [2][4] when
  two sources support it.
- If the sources do not answer the question, reply with exactly {NOT_COVERED} and nothing else.
- If the sources only partly answer it, answer that part and say plainly what they don't cover.
- Never predict how a tribunal will decide, and never tell the person what they "will win".
- Keep it short: a direct answer first, then the key conditions or exceptions. No headings.
"""


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[Hit]  # only the sources actually cited, in citation order
    covered: bool


def format_sources(hits: list[Hit]) -> str:
    return "\n\n".join(
        f"[{n}] {h.source_title} | {h.heading_path}\n{h.body}" for n, h in enumerate(hits, start=1)
    )


def check_answer(raw: str, hits: list[Hit]) -> Answer:
    text = raw.strip()
    cited = [int(n) for n in _CITATION.findall(text)]
    if text == NOT_COVERED or not cited:
        return Answer(NOT_COVERED_MESSAGE, [], covered=False)
    if any(n < 1 or n > len(hits) for n in cited):
        raise ValueError(f"answer cites a source that was not supplied: {sorted(set(cited))}")

    # renumber to the cited sources only, in first-cited order
    order: list[int] = []
    for n in cited:
        if n not in order:
            order.append(n)
    renumber = {old: new for new, old in enumerate(order, start=1)}
    text = _CITATION.sub(lambda m: f"[{renumber[int(m.group(1))]}]", text)
    return Answer(text, [hits[n - 1] for n in order], covered=True)


def answer(question: str, hits: list[Hit], client: anthropic.Anthropic | None = None) -> Answer:
    if not hits:
        return Answer(NOT_COVERED_MESSAGE, [], covered=False)
    if client is None:
        key = settings.anthropic_api_key
        client = anthropic.Anthropic(api_key=key.get_secret_value() if key else None)
    msg = client.messages.create(
        model=settings.answer_model,
        max_tokens=2000,  # the model may think before writing; that comes out of this budget
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Sources:\n\n{format_sources(hits)}\n\nQuestion: {question}",
        }],
    )
    if msg.stop_reason == "max_tokens":
        # never show a half-finished legal explanation
        raise RuntimeError("answer was cut off at the token limit")
    raw = "".join(block.text for block in msg.content if block.type == "text")
    return check_answer(raw, hits)

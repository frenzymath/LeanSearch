import asyncio
import logging
import os
import re
from dataclasses import dataclass
from json import JSONDecodeError
import xml.etree.ElementTree as ET

import jinja2
from jinja2 import Environment, FileSystemLoader
from jixia.structs import DeclarationKind, LeanName, pp_name
from openai import AsyncOpenAI
from prompt.metaprogramming import metaprogramming_prompt

logger = logging.getLogger(__name__)


@dataclass
class TranslatedItem:
    name: LeanName
    signature: str
    value: str | None
    docstring: str | None
    kind: DeclarationKind

    informal_name: str | None
    informal_description: str | None

    # The "description" field is a copypaste of the more appropriately named "signature" field, it's here for backwards compatibility, and can be removed when all prompts are switch to using the "signature" field.
    description: str

@dataclass
class TranslationInput:
    name: LeanName
    signature: str
    value: str | None
    docstring: str | None
    kind: DeclarationKind
    header: str

    neighbor: list[TranslatedItem]
    dependency: list[TranslatedItem]

    @property
    def value_matters(self):
        return self.kind in ["classInductive", "definition", "inductive", "structure"]


class TranslationEnvironment:
    def __init__(self, model: str):
        self.env = Environment(
            loader=FileSystemLoader(os.environ.get("PROMPT_DIR", "prompt")),
            enable_async=True,
            undefined=jinja2.StrictUndefined,
        )
        self.env.filters["pp_name"] = pp_name
        self.template = {kind: self.env.get_template(f"{kind}.md.j2") for kind in ["theorem", "definition", "instance"]}
        self.client = AsyncOpenAI()
        self.model = model
        self.pattern_name = re.compile(r"\*\*Informal name:?\*\*\s*(.*)")
        self.pattern_description = re.compile(
            r"\*\*Informal statement:?\*\*\s(.*?)\*\*End of informal statement\*\*",
            re.DOTALL,
        )

    async def translate(self, data: TranslationInput) -> tuple[str, str] | None:
        if data.kind == "instance":
            kind = "instance"
        else:
            kind = "definition" if data.value_matters else "theorem"
        prompt = await self.template[kind].render_async(input=data)
        if os.environ["DRY_RUN"] == "true":
            logger.info("DRY_RUN:skipped informalization: %s", data.name)
            return "Fake Name", f"Fake Description\nPrompt:\n{data}"
        for _ in range(5):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                    # ___Why don't we use `response_format={ 'type': 'json_object' }`?
                    #    DeepSeek support for json is rather limited at the moment, in our case it will be raising parse errors on LaTeX escape characters.
                    stream=False,
                )
            except JSONDecodeError:  # DeepSeek API is not available right now
                logger.info("while translating %s: service unavailable; retrying", data.name)
                await asyncio.sleep(1)
                continue
            answer = response.choices[0].message.content
            try:
                name = self.pattern_name.search(answer).group(1)
                description = self.pattern_description.search(answer).group(1)
            except AttributeError:  # unable to parse the result, at least one of the regex did not match
                logger.info("while translating %s: unable to parse the result; retrying", data.name)
                continue
            return name.strip(), description.strip()

import asyncio
import os
import re
from json import JSONDecodeError

import jinja2
from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI


class Augmentor:
    def __init__(self, model: str):
        self.env = Environment(
            loader=FileSystemLoader(os.environ.get("PROMPT_DIR", "prompt")),
            enable_async=True,
            undefined=jinja2.StrictUndefined,
        )
        self.template = self.env.get_template("augment_prompt.j2")
        with open("prompt/augment_assistant.txt") as fp:
            self.assistant_prompt = fp.read()
        self.client = AsyncOpenAI()
        self.model = model
        self.pattern = re.compile(r'Paraphrase:\s*"([^"]+)"')

    async def augment(self, user_input: str) -> str | None:
        prompt = await self.template.render_async(input=user_input)
        response = None
        for _ in range(5):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "assistant", "content": self.assistant_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    stream=False,
                )
            except JSONDecodeError:
                await asyncio.sleep(1)
                continue
            break
        if response is None:
            return user_input
        answer = response.choices[0].message.content
        try:
            return self.pattern.search(answer).group(1)
        except AttributeError:
            return answer

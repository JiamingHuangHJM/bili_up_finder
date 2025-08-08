import os
from abc import ABC, abstractmethod

from openai import OpenAI


class Assistant(ABC):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        instructions: str | None = None,
        verbose: bool = False,
    ):
        self.model = model
        self.api_key = api_key
        self.instructions = instructions
        self.verbose = verbose

    @abstractmethod
    def setup_client():
        pass

    @abstractmethod
    def ask(self, user_input: str) -> str:
        """
        Abstract method to assist with a given task.
        :param task: The task to assist with.
        :return: A string response from the assistant.
        """
        pass


class DeepSeekAssistant(Assistant):
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str | None = None,
        instructions: str | None = None,
        verbose: bool = False,
    ):
        super().__init__(model, api_key, instructions, verbose)
        self.setup_client()

    def setup_client(self):
        if not self.api_key:
            if not (api_key_from_env := os.getenv("DEEPSEEK_API_KEY")):
                raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")
            self.api_key = api_key_from_env

        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

    def ask(self, user_input: str) -> str:
        if self.verbose:
            reason = " 以及在yes或no之后, 告诉我你为什么这么认为。"
            self.instructions += f" {reason}"

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": user_input},
            ],
            stream=False,
        )

        return response.choices[0].message.content


class OpenAIAssistant(Assistant):
    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: str | None = None,
        instructions: str | None = None,
        verbose: bool = False,
    ):
        super().__init__(model, api_key, instructions, verbose)
        self.setup_client()

    def setup_client(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = OpenAI()

    def ask(self, user_input: str) -> str:
        if self.verbose:
            reason = " 在yes或no之后, 告诉我你为什么这么认为。"
            self.instructions += f" {reason}"

        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=user_input,
        )

        return response.output_text

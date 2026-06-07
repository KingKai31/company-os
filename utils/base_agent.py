import os
import anthropic
from dotenv import load_dotenv
from utils.shared_brain import write_state, read_state, read_all_states

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

class BaseAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.confidence = 100

    def think(self, prompt, system="You are a helpful business AI agent.", max_tokens=1000):
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def score_confidence(self, output):
        prompt = f"""Rate the quality and confidence of this output from 0 to 100.
        Output: {output}
        Reply with just a number between 0 and 100."""
        score = self.think(prompt)
        try:
            self.confidence = int(''.join(filter(str.isdigit, score)))
        except:
            self.confidence = 75
        return self.confidence

    def write(self, data):
        write_state(self.agent_id, data)

    def read(self, agent_id):
        return read_state(agent_id)

    def read_all(self):
        return read_all_states()

    def run(self, context):
        raise NotImplementedError("Each agent must implement run()")
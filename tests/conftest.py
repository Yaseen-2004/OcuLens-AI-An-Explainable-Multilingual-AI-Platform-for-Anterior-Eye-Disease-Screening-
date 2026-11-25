import os

# Tests never call the paid LLM API, even when a key is configured on the machine.
os.environ["OCULENS_ASSISTANT"] = "template"

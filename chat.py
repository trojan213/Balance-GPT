import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_API_KEY"],
)

completion = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3.2-Exp:novita",
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?"
        }
    ],
)

print(completion.choices[0].message)
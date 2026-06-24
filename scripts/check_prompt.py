from rag.prompts import QUESTION_GENERATION_PROMPT

filled = QUESTION_GENERATION_PROMPT.invoke({"context": "FastAPI, JWT, PostgreSQL"})
print(filled.to_string())

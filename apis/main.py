from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Numbers(BaseModel):
    a: int
    b: int

@app.get("/")
def home():
    return {"message": "Hello Shudip! Your API is working 🚀"}

@app.post("/add")
def add_numbers(data: Numbers):
    result = data.a + data.b
    return {
        "operation": "addition",
        "a": data.a,
        "b": data.b,
        "result": result
    }
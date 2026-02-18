from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello Shudip! Your API is working 🚀"}

@app.get("/add")
def add(a: int, b: int):
    return {"result": a + b}



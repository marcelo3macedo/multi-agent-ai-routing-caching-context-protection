from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.presentation.api.routes import router as api_router

app = FastAPI(
    title="Multi-Agent AI Routing, Caching & Context Protection API",
    description="Servidor FastAPI com Roteamento de Intenções (Gemini 1.5 Flash 8B) e Interceptador de Cache Redis",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas sob o prefixo /api/v1
app.include_router(api_router, prefix="/api/v1")

# Adiciona rota WebSocket no nível raiz para manter compatibilidade com /ws/chat
from src.presentation.api.routes import websocket_chat_endpoint
app.add_api_websocket_route("/ws/chat", websocket_chat_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.presentation.api.server:app", host="127.0.0.1", port=8000, reload=True)

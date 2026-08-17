# Arquitetura com Roteamento de Intenções, Interceptador de Cache (Redis) & Google ADK

Infraestrutura de microsserviços e inteligência artificial conversacional utilizando **FastAPI**, **Google Agent Development Kit (Google ADK)**, **Classificador de Intenção (Gemini 1.5 Flash 8B)** e **Redis (Exact & Semantic Cache)** com suporte completo a **Docker** e **Docker Compose**.

---

## 🏛️ Estrutura do Projeto (Clean Architecture)

```
.
├── Dockerfile                         # Containerização da API FastAPI Python
├── docker-compose.yml                 # Orquestração dos serviços FastAPI + Redis 7
├── .dockerignore                      # Arquivos ignorados no contexto de build do Docker
├── requirements.txt                   # Dependências do projeto
├── run_benchmark.py                   # Script de benchmark de latência e consumo de tokens
├── cli.py                             # Interface REPL no Terminal CLI (Typer/Rich)
└── src/
    ├── domain/                        # Entidades e Interfaces do Domínio
    ├── infrastructure/                # Configurações, Redis Cache, Gemini 1.5 Flash 8B e Google ADK
    ├── application/                   # Casos de Uso (ProcessChatMessageUseCase)
    └── presentation/                  # Controladores FastAPI (REST / WebSocket) e CLI Terminal
```

---

## 🐳 Executando com Docker Compose (Recomendado)

### 1. Iniciar todos os serviços (API FastAPI + Redis)

```bash
docker compose up -d
```

### 2. Verificar os logs dos containers

```bash
docker compose logs -f
```

### 3. Parar os serviços

```bash
docker compose down
```

---

## 🛠️ Execução Local (sem Docker)

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor FastAPI
python cli.py server

# Iniciar interface REPL interativa
python cli.py

# Executar benchmark
python run_benchmark.py

# Executar suíte de testes
pytest
```

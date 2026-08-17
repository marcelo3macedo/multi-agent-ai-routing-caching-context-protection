# Multi-Agent AI Routing, Caching & Context Protection

Assistente conversacional da **TechCorp Solutions**, uma empresa de indicação de filmes. O projeto é, ao mesmo tempo, o produto (um agente que recomenda filmes e responde dúvidas institucionais) e um estudo de arquitetura sobre **como servir esse tipo de agente gastando o mínimo possível de tokens e latência**, sem abrir mão de respostas de qualidade.

Três pilares sustentam isso:

- **Cache Interceptador (Redis)** — respostas repetidas ou muito parecidas (`exact` + `semantic`) voltam em poucos milissegundos, sem tocar em LLM nenhum.
- **Roteamento de Intenção com modelo leve** — uma heurística/classificador barato decide *antes* de qualquer chamada cara: isso é uma saudação? Uma dúvida institucional? Uma busca de filme? Só o necessário chega ao modelo grande.
- **Multi-agente (Google ADK)** — em vez de um único agente monolítico com um prompt gigante tentando cobrir tudo, um `RootAgent` delega para especialistas pequenos e focados (`InstitutionalAgent`, `MovieCatalogAgent`), cada um com contexto e ferramentas só do seu domínio.

O objetivo declarado do projeto é **eficiência**: menos tokens, menos latência, sem perder precisão — e o `run_benchmark.py` existe justamente para medir isso comparando a versão monolítica ingênua com a versão roteada/cacheada.

---

## 🛠️ Tecnologias

- **[FastAPI](https://fastapi.tiangolo.com/)** — API REST (`/api/v1/chat`) e WebSocket (`/ws/chat`).
- **[Google ADK](https://google.github.io/adk-docs/)** — orquestração multi-agente (`RootAgent` + sub-agentes), tools e sessões.
- **Gemini** — LLM por trás dos agentes e do classificador de intenção.
- **[Redis](https://redis.io/)** — cache interceptador (exact + semantic), com fallback em memória.
- **[TMDB API](https://www.themoviedb.org/documentation/api)** — catálogo real de filmes usado pelo `MovieCatalogAgent`.
- **[Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/)** — CLI/REPL no terminal, com badges de roteamento.
- **Docker / Docker Compose** — empacota API + Redis para rodar com um comando.
- **Pytest** — suíte de testes (unidade + integração).

---

## 🐳 Executando com Docker Compose (Recomendado)

```bash
docker compose up -d
```

---

## 💬 Exemplos de Conversas

Os exemplos abaixo são transcrições reais (CLI local, `python cli.py`), mostrando o badge de roteamento e as métricas de cada resposta.

### 1. Saudação — identificação semântica pelo modelo leve

```
Você: Bom dia

💬 SAUDAÇÃO (ROTEAMENTO LEVE)
Olá! Bem-vindo à TechCorp Solutions, sua empresa de indicação de filmes! 🎬
Quer saber sobre algum filme ou sobre a empresa?

Intenção: GREETING | Cache: MISS | Tokens: 0 | Latência: ~1 ms
```

A heurística do `LightweightIntentClassifier` reconhece "bom dia" como saudação em menos de 2ms — **nenhuma chamada de LLM acontece**. A resposta é determinística e já é gravada no cache para a próxima vez.

### 2. Cache Hit — a mesma saudação, de novo

```
Você: Bom dia

⚡ CACHE HIT
Olá! Bem-vindo à TechCorp Solutions, sua empresa de indicação de filmes! 🎬
Quer saber sobre algum filme ou sobre a empresa?

Intenção: CACHED | Cache: HIT_SEMANTIC | Tokens: 0 | Latência: ~0.2 ms
```

Antes de qualquer classificação, o *use case* já consulta o cache Redis. Na segunda vez, a resposta nem chega a ser roteada — vem direto do cache, ~5x mais rápido que o primeiro atendimento (que já era rápido) e continua em **0 tokens**.

### 3. "Quais filmes do Homem-Aranha tem?"

```
Você: Quais filmes do Homem-Aranha tem?

🎬 FILMES → MovieCatalogAgent (TMDB)
Temos diversos filmes do Homem-Aranha no catálogo, entre animações e
produções em live-action.

O lançamento mais recente é "Homem-Aranha: Um Novo Dia", que estreou em
julho de 2026. Já o mais bem avaliado pelo público é a animação
"Homem-Aranha: No Aranhaverso" (2018), com nota média de 8,4.

Se quiser saber mais sobre algum deles ou busca uma recomendação
específica, é só avisar!

Intenção: MOVIE_SEARCH | Cache: MISS | Tokens: ~3.500 | Latência: ~9.8 s
```

O `RootAgent` delega para o `MovieCatalogAgent`, que chama a tool `search_movies` contra o TMDB real. Seguindo a instrução do agente, ele destaca primeiro o lançamento mais recente **já lançado** (comparando com a data atual injetada no prompt) e comenta o mais bem avaliado — sem listar os 10+ resultados que a tool retornou.

### 4. "Me indique filmes do Tom Cruise"

```
Você: Me indique filmes do Tom Cruise

🎬 FILMES → MovieCatalogAgent (TMDB)
Aqui estão algumas das melhores recomendações de filmes estrelados por
Tom Cruise:

• Top Gun: Maverick (2022) — um dos maiores sucessos de crítica e público
  do ator, reprisando o papel do piloto "Maverick" Mitchell.
• Franquia Missão: Impossível — destaque para o clássico Missão:
  Impossível (1996) e o recente O Acerto Final (2025).
• Top Gun - Ases Indomáveis (1986) — o clássico dos anos 80 que
  consagrou Tom Cruise como astro de Hollywood.

Algum desses gêneros de ação e aventura é o seu favorito?

Intenção: MOVIE_SEARCH | Cache: MISS | Tokens: ~3.550 | Latência: ~18.5 s
```

Interessante aqui: a tool `search_movies` busca por **título de filme**, não por ator — buscar `"Tom Cruise"` direto no TMDB retorna sobretudo um documentário sobre ele. O agente percebeu isso sozinho e fez *follow-up calls* específicos (`"Top Gun"`, `"Missão Impossível"`) para montar a resposta certa. Esse raciocínio em múltiplos passos é decidido pelo próprio ADK, não hardcoded no roteamento.

### 5. "Quais filmes o Tom Holland fez?"

```
Você: Quais filmes o Tom Holland fez?

🎬 FILMES → MovieCatalogAgent (TMDB)
Tom Holland é mundialmente conhecido por interpretar o Homem-Aranha no
Universo Cinematográfico da Marvel.

Na franquia do herói, o filme lançado mais recentemente é
"Homem-Aranha: Um Novo Dia" (julho de 2026). Já o mais bem avaliado de
sua trajetória como o herói é "Homem-Aranha: Sem Volta Para Casa" (2021),
nota 7,94 no TMDB.

Além da trilogia e do novo longa do herói, ele também estrelou
produções como Uncharted: Fora do Mapa (2022).

Intenção: MOVIE_SEARCH | Cache: MISS | Tokens: ~4.650 | Latência: ~19.9 s
```

### 6. "Filmes do Tom Holland que não sejam Homem-Aranha"

```
Você: Filmes do Tom Holland que não sejam Homem-Aranha

🎬 FILMES → MovieCatalogAgent (TMDB)
Além do papel de Homem-Aranha, Tom Holland protagonizou diversos outros
filmes de destaque:

• O Impossível (2012) — drama baseado em fatos reais sobre o tsunami de
  2004 na Tailândia, um dos primeiros papéis marcantes da carreira dele.
• Uncharted: Fora do Mapa (2022) — adaptação dos videogames, no papel do
  caçador de tesouros Nathan Drake.
• O Diabo de Cada Dia (2020) — suspense sombrio sobre um jovem tentando
  proteger a família em uma cidade marcada pela corrupção.

Se quiser saber mais sobre algum deles ou busca outro gênero
específico, é só avisar!

Intenção: MOVIE_SEARCH | Cache: MISS | Tokens: ~3.270 | Latência: ~14.4 s
```

O agente pesquisou vários títulos (inclusive um resultado espúrio, "Missão: Impossível", que o TMDB retornou por similaridade textual com "Impossível") e **filtrou sozinho** o que não fazia sentido antes de responder — o Homem-Aranha e o resultado errado ficaram de fora.

### 7. "Tem algum filme do Tom Holland com o cara do Crepúsculo?"

```
Você: Tem algum filme do Tom Holland com o cara do Crepúsculo?

🎬 FILMES → MovieCatalogAgent (TMDB)
Sim! Tom Holland e Robert Pattinson (o astro de Crepúsculo) atuam
juntos no filme O Diabo de Cada Dia (The Devil All the Time), lançado
em 2020.

É um suspense psicológico sombrio e bem avaliado, no qual o personagem
de Tom Holland precisa enfrentar figuras sinistras em uma pequena
cidade para proteger as pessoas que ama.

Intenção: MOVIE_SEARCH | Cache: MISS | Tokens: ~1.600 | Latência: ~12.9 s
```

Esse caso ilustra um limite honesto da arquitetura atual: a tool `search_movies` **não retorna elenco** (só `id`, `title`, `overview`, `release_date`, `vote_average` — ver Smart Context Truncation abaixo). A associação "Robert Pattinson = o cara do Crepúsculo" e o fato de ele estar no elenco desse filme vêm do conhecimento próprio do modelo, não do TMDB; o que a tool garante é que **título, data de lançamento e nota são reais e verificados**, não inventados.

---

## 🧩 Decisões Técnicas para Economia de Tokens

### 1. Modelo leve para detectar a intenção antes do modelo caro

`LightweightIntentClassifier` (`src/infrastructure/classifiers/lightweight_classifier.py`) resolve saudações, e reconhece padrões institucionais/filmes por heurística de palavras-chave em **sub-2ms**, sem nenhuma chamada de LLM. Só quando a heurística não é conclusiva ele cai para um modelo pequeno (Gemini Flash) — nunca o modelo "pesado" que efetivamente conversa com o usuário. Isso significa que a decisão de roteamento em si é praticamente gratuita comparada ao custo de uma chamada completa ao `RootAgent`.

### 2. Cache interceptador antes de tudo

`ProcessChatMessageUseCase.execute()` consulta o cache Redis (exact + semantic, via `difflib`) **antes** de classificar ou rotear qualquer coisa. Perguntas repetidas ou muito parecidas nunca chegam ao classificador nem ao ADK — voltam em poucos milissegundos e **0 tokens**. Saudações resolvidas pelo roteamento leve são gravadas no cache com TTL de 24h; respostas do ADK (institucional/filmes), com TTL de 1h.

### 3. Multi-agente em vez de um prompt monolítico

Em vez de um único agente com uma instrução gigante tentando cobrir saudação + institucional + filmes (o baseline `BaseRootAgent`, mantido só para efeito de comparação no benchmark), o `RootAgent` real delega para sub-agentes especialistas:

- **`InstitutionalAgent`** — instrução curta, uma única tool (`get_company_info`) sobre uma base JSON estática.
- **`MovieCatalogAgent`** — instrução curta, uma única tool (`search_movies`) sobre o TMDB.

Cada sub-agente só carrega o contexto do seu próprio domínio. Isso mantém os prompts pequenos e focados, em vez de um único prompt gigante sendo reenviado (e pago) em toda conversa, não importa o assunto.

### 4. Smart Context Truncation no catálogo de filmes

O TMDB devolve payloads grandes por filme (`popularity`, `backdrop_path`, `adult`, `genre_ids`, `poster_path`, `vote_count`, `original_language`, `video`...). A tool `search_movies` (`tmdb_tool.py`) filtra isso para uma lista branca de 5 campos — `id`, `title`, `overview`, `release_date`, `vote_average` — antes de devolver ao agente. Isso protege a janela de contexto da LLM contra *context overflow* em buscas com muitos resultados, e reduz diretamente os tokens de entrada em cada chamada de tool.

### 5. Contexto de data injetado no prompt

Um LLM não sabe "que dia é hoje" nem tem conhecimento atualizado sobre lançamentos recentes. Em vez de deixar o modelo adivinhar, `create_movie_catalog_agent()` injeta a data real (`date.today()`) diretamente na instrução do `MovieCatalogAgent` (`"A data de hoje é {current_date}..."`). É esse contexto que permite ao agente comparar a `release_date` retornada pela tool com a data de hoje e responder corretamente se um filme "já foi lançado" ou ainda está por vir — sem isso, ele erraria facilmente para lançamentos recentes.

### 6. Tratamento de erro amigável, sem gastar contexto extra com detalhes técnicos

Falhas transitórias do provedor do modelo (rate limit, sobrecarga — HTTP 429/500/502/503/504) são convertidas em uma mensagem curta e no tom da marca (`error_handling.py`), em vez de propagar o payload de erro bruto da API para o usuário. O erro técnico completo (com stack trace) é logado separadamente — apenas no processo/container do servidor, nunca na conversa do usuário — preservando contexto de debug sem poluir (ou gastar tokens de) a experiência de chat.

### 7. Logs de execução isolados do canal de conversa

Cada chamada de tool (`get_company_info`, `search_movies`) é logada via callbacks do ADK (`tool_logging.py`), mas **apenas onde o processo é configurado para isso** — o servidor/container. O CLI interativo silencia esse canal (e os avisos internos do próprio ADK) para manter a conversa limpa, sem misturar telemetria de execução com a resposta que o usuário efetivamente lê.

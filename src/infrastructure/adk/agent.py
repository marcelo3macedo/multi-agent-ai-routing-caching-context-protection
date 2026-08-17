from google.adk.agents import LlmAgent
from src.infrastructure.config.settings import Settings
from src.infrastructure.adk.mock_llm import register_mock_llm
from src.infrastructure.adk.institutional_agent import create_institutional_agent
from src.infrastructure.adk.movie_agent import create_movie_catalog_agent
from src.infrastructure.adk.prompts import MONOLITHIC_SYSTEM_INSTRUCTION, ROOT_SYSTEM_INSTRUCTION

def create_base_root_agent(model_name: str = None) -> LlmAgent:
    """
    Cria a instância do BaseRootAgent usando o Google ADK (LlmAgent).
    """
    register_mock_llm()
    effective_model = model_name or Settings.get_effective_model()
    
    agent = LlmAgent(
        name="BaseRootAgent",
        model=effective_model,
        instruction=MONOLITHIC_SYSTEM_INSTRUCTION.strip(),
        tools=[]
    )

    return agent

def create_root_agent(model_name: str = None) -> LlmAgent:
    """
    Cria o RootAgent multi-agente: encaminha dúvidas institucionais ao InstitutionalAgent
    (apoiado pela base de conhecimento estática company_info.json), buscas/recomendações
    de filmes ao MovieCatalogAgent (apoiado pela TMDBMovieTool) e trata saudações e
    demais assuntos gerais diretamente.
    """
    register_mock_llm()
    effective_model = model_name or Settings.get_effective_model()

    institutional_agent = create_institutional_agent(model_name=effective_model)
    movie_agent = create_movie_catalog_agent(model_name=effective_model)

    return LlmAgent(
        name="RootAgent",
        model=effective_model,
        instruction=ROOT_SYSTEM_INSTRUCTION.strip(),
        sub_agents=[institutional_agent, movie_agent],
        tools=[]
    )

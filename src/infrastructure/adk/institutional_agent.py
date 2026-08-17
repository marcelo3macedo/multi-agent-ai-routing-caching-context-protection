import json
from pathlib import Path
from functools import lru_cache
from google.adk.agents import LlmAgent
from src.infrastructure.config.settings import Settings
from src.infrastructure.adk.prompts import INSTITUTIONAL_SYSTEM_INSTRUCTION

COMPANY_INFO_PATH = Path(__file__).parent / "knowledge" / "company_info.json"

TOPIC_ALIASES = {
    "quem_somos": ["quem somos", "quem é", "sobre", "empresa", "historia", "fundação"],
    "servicos": ["servico", "serviços", "produtos", "o que vocês fazem", "solucoes"],
    "contato": ["contato", "telefone", "email", "e-mail", "endereco", "site", "falar com"],
    "missao": ["missao", "missão", "valores", "proposito"],
}

@lru_cache(maxsize=1)
def load_company_info() -> dict:
    """Carrega a base de conhecimento institucional estática (JSON)."""
    with open(COMPANY_INFO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_company_info(topic: str) -> str:
    """
    Consulta a base de conhecimento institucional da TechCorp Solutions.

    Args:
        topic: Assunto institucional desejado, ex: "quem somos", "serviços", "contato" ou "missão".

    Returns:
        O trecho da base de conhecimento correspondente ao assunto, ou a lista de assuntos
        disponíveis caso o termo não seja reconhecido.
    """
    info = load_company_info()
    topic_lower = topic.lower().strip()

    for key, aliases in TOPIC_ALIASES.items():
        if topic_lower == key or any(alias in topic_lower for alias in aliases):
            return info[key]

    available = ", ".join(info.keys())
    return f"Assunto não encontrado na base institucional. Assuntos disponíveis: {available}."


def create_institutional_agent(model_name: str = None) -> LlmAgent:
    """
    Cria o InstitutionalAgent: sub-agente ADK especializado em dúvidas institucionais,
    apoiado pela base de conhecimento estática company_info.json.
    """
    effective_model = model_name or Settings.get_effective_model()

    return LlmAgent(
        name="InstitutionalAgent",
        model=effective_model,
        instruction=INSTITUTIONAL_SYSTEM_INSTRUCTION.strip(),
        description=(
            "Especialista em dúvidas institucionais sobre a TechCorp Solutions "
            "(quem somos, serviços, missão e contato)."
        ),
        tools=[get_company_info],
    )

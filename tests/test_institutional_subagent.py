from src.infrastructure.adk.institutional_agent import (
    create_institutional_agent,
    get_company_info,
    load_company_info,
)
from src.infrastructure.adk.agent import create_root_agent, create_base_root_agent


def test_company_info_knowledge_base_has_expected_topics():
    info = load_company_info()
    assert "quem_somos" in info
    assert "servicos" in info
    assert "contato" in info
    assert "TechCorp" in info["quem_somos"]


def test_get_company_info_resolves_known_topics():
    assert "TechCorp" in get_company_info("quem somos")
    assert "TechCorp" in get_company_info("empresa")
    assert "contato@techcorpsolutions.com.br" in get_company_info("contato")
    assert "serviços" in get_company_info("o que vocês fazem").lower() or "servi" in get_company_info("servicos").lower()


def test_get_company_info_unknown_topic_lists_available_topics():
    result = get_company_info("assunto totalmente aleatorio")
    assert "não encontrado" in result.lower()
    assert "quem_somos" in result


def test_create_institutional_agent_is_scoped_and_tooled():
    agent = create_institutional_agent(model_name="mock-model-gemini-3.6-flash")
    assert agent.name == "InstitutionalAgent"
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "get_company_info"
    assert "institucional" in agent.instruction.lower()


def test_create_root_agent_delegates_to_institutional_subagent():
    root_agent = create_root_agent(model_name="mock-model-gemini-3.6-flash")
    assert root_agent.name == "RootAgent"
    assert len(root_agent.sub_agents) == 1
    assert root_agent.sub_agents[0].name == "InstitutionalAgent"


def test_monolithic_base_root_agent_untouched_by_subagent_changes():
    """O baseline monolítico usado no benchmark não deve ganhar sub-agentes."""
    base_agent = create_base_root_agent(model_name="mock-model-gemini-3.6-flash")
    assert base_agent.name == "BaseRootAgent"
    assert base_agent.sub_agents == []

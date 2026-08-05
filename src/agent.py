from google.adk.agents import LlmAgent
from src.config import Config
from src.mock_llm import register_mock_llm

MONOLITHIC_SYSTEM_INSTRUCTION = """
Você é o BaseRootAgent, um assistente virtual generalista monolítico para a empresa TechCorp Solutions.
Sua responsabilidade é atender a TODAS as requisições enviadas pelo usuário em um único ponto de contato,
sem auxílio de roteadores, especialistas ou ferramentas externas.

Diretrizes de Atendimento:
1. Saudações e Cortesia: Responda a comprimentos como "Bom dia", "Boa tarde", "Olá" de forma muito cortês e formal.
2. Informações Institucionais: A TechCorp Solutions é uma empresa fundada em 2020, líder em tecnologia de Inteligência Artificial e automação de processos corporativos.
3. Recomendações Gerais: Forneça sugestões de entretenimento, filmes, livros ou assuntos cotidianos sempre que solicitado.
4. Suporte Geral: Caso o usuário faça perguntas genéricas ou fora do escopo corporativo, responda de forma prestativa e concisa.

Atenção: Você deve processar qualquer mensagem diretamente nesta mesma instrução genérica.
"""

def create_base_root_agent(model_name: str = None) -> LlmAgent:
    """
    Cria a instância do BaseRootAgent usando o Google ADK (LlmAgent).
    
    Este agente é monolítico: não possui ferramentas (tools), não possui roteamento
    especializado e nem sub-agentes atrelados.
    """
    # Garante o registro do mock se estiver ativo
    register_mock_llm()
    
    effective_model = model_name or Config.get_effective_model()
    
    agent = LlmAgent(
        name="BaseRootAgent",
        model=effective_model,
        instruction=MONOLITHIC_SYSTEM_INSTRUCTION.strip(),
        tools=[]  # Sem ferramentas atreladas neste cenário base
    )
    
    return agent

from app.agent.core import Agent
from app.core.config import get_settings


def agent_from_settings() -> Agent:
    """The LLM client every AI port is backed by, configured from settings.

    One place builds it, so the parser, the categoriser and the goal mapper
    always talk to the same model with the same switches.
    """
    settings = get_settings()
    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    return Agent(
        model=settings.llm_model,
        api_key=api_key,
        api_base=settings.llm_api_base,
        disable_reasoning=settings.llm_disable_reasoning,
        disable_json_schema=settings.llm_disable_json_schema,
        vertex_project=settings.vertex_project,
        vertex_location=settings.vertex_location,
    )

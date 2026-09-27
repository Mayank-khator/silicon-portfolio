from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    cors_origins: tuple[str, ...] = ('http://localhost:3000',)
    llm_provider: str = 'none'
    allow_external_llm: bool = False
    llm_model: str = ''
    ollama_base_url: str = 'http://ollama:11434'

    @classmethod
    def from_env(cls):
        return cls(
            supabase_url=os.getenv('SUPABASE_URL', '').rstrip('/'),
            supabase_publishable_key=os.getenv('SUPABASE_PUBLISHABLE_KEY', os.getenv('SUPABASE_ANON_KEY', '')),
            cors_origins=tuple(x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',') if x.strip()),
            llm_provider=os.getenv('LLM_PROVIDER', 'none').lower(),
            allow_external_llm=os.getenv('ALLOW_EXTERNAL_LLM', 'false').lower() == 'true',
            llm_model=os.getenv('LLM_MODEL', ''),
            ollama_base_url=os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434'),
        )

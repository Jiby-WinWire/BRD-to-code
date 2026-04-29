# Language code generator registry
from typing import Dict, Type
from src.agents.base_code_generator import BaseCodeGenerator
from src.agents.python_code_generator import PythonCodeGenerator
from src.agents.csharp_code_generator import CSharpCodeGenerator

class CodeGeneratorRegistry:
    _registry: Dict[str, Type[BaseCodeGenerator]] = {}

    @classmethod
    def register(cls, language: str, generator: Type[BaseCodeGenerator]):
        cls._registry[language.lower()] = generator

    @classmethod
    def get_generator(cls, language: str) -> Type[BaseCodeGenerator]:
        lang = language.lower()
        if lang not in cls._registry:
            raise ValueError(f"No code generator registered for language: {language}")
        return cls._registry[lang]

# Register built-in generators
CodeGeneratorRegistry.register("python", PythonCodeGenerator)
CodeGeneratorRegistry.register("csharp", CSharpCodeGenerator)
# Add more with: CodeGeneratorRegistry.register("newlang", NewLangCodeGenerator)

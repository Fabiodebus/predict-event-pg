import enum


class LLMRole(str, enum.Enum):
    LONG_CONTEXT_REASONING = "long_context_reasoning"
    STRUCTURED_EXTRACTION = "structured_extraction"
    MESSAGE_GENERATION = "message_generation"

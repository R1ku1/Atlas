from transformers import AutoTokenizer

class EmbeddingTokenizer:
    """Wraps a HuggingFace tokenizer for token counting."""
    def __init__(self, model_name: str = "mixedbread-ai/mxbai-embed-large-v1"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def tokenize(self, text: str):
        return self.tokenizer.tokenize(text)
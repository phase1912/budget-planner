"""Which reader reads receipts: the model, or the corpus for tests (F0.11.2)."""

from pathlib import Path

from app.adapters.categorisation_agent import ItemCategoriserAdapter
from app.adapters.corpus_reader import CorpusCases, CorpusCategoriser, CorpusReader
from app.adapters.vision_agent import VisionAgentAdapter
from app.agent.factory import agent_from_settings
from app.core.config import get_settings
from app.ports.categorisation import ItemCategoriserPort
from app.ports.parsing import ReceiptParserPort, ReceiptRecheckerPort

_cases: dict[str, CorpusCases] = {}


def _corpus() -> CorpusCases:
    folder = get_settings().reading_corpus_dir
    if folder not in _cases:
        _cases[folder] = CorpusCases(Path(folder))
    return _cases[folder]


def receipt_reader() -> tuple[ReceiptParserPort, ReceiptRecheckerPort]:
    """The parser and rechecker the configuration chose; one object serves both."""
    if get_settings().reading_engine == "corpus":
        corpus_reader = CorpusReader(_corpus())
        return corpus_reader, corpus_reader
    model_reader = VisionAgentAdapter(agent_from_settings())
    return model_reader, model_reader


def item_categoriser() -> ItemCategoriserPort:
    """The categoriser the configuration chose (BRD C1)."""
    if get_settings().reading_engine == "corpus":
        return CorpusCategoriser(_corpus())
    return ItemCategoriserAdapter(agent_from_settings())

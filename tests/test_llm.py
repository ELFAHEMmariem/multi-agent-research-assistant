
from langchain_groq import ChatGroq

from app.llm import get_llm


def test_llm_configuration():
    llm = get_llm()

    assert isinstance(llm, ChatGroq)
    assert llm.model_name

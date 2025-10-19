from types import SimpleNamespace
import rag_kmk.chat_flow.llm_interface as llm_interface


def test_generate_answer_monkeypatch(monkeypatch):
    # Prepare a fake chroma_collection and query result
    fake_docs = ["Doc excerpt 1.", "Doc excerpt 2."]

    def fake_retrieve(chroma_collection, query, n_results=10, return_only_docs=False):
        return fake_docs

    monkeypatch.setattr('rag_kmk.chat_flow.llm_interface.retrieve_chunks', fake_retrieve)

    # Fake chat object with send_message returning an object with .text
    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeChat:
        def __init__(self):
            self.last_message = None

        def send_message(self, content):
            self.last_message = content
            return FakeResponse(text="This is a fake LLM answer")

    fake_chat = FakeChat()

    output = llm_interface.generateAnswer(fake_chat, chroma_collection=None, query="What is test?", n_results=2, only_response=True)

    assert output == "This is a fake LLM answer"
    # Ensure the chat received prompt + context
    assert "QUESTION: What is test?" in fake_chat.last_message
    assert "Doc excerpt 1." in fake_chat.last_message

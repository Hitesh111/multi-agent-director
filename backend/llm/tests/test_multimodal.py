import pytest
import json
from llm.schemas import LLMConfig, Message
from llm.providers.deepseek import DeepSeekProvider


def test_multimodal_payload_building():
    provider = DeepSeekProvider({
        "api_key": "fake_key",
        "api_base": "https://api.fake.com/v1",
        "default_model": "model-1",
    })
    
    # Standard text message
    msg1 = Message(role="user", content="Hello, world!")
    
    # Multimodal image and text message
    multimodal_content = json.dumps({
        "type": "multimodal",
        "text": "Describe this image",
        "image_url": "https://example.com/test.png"
    })
    msg2 = Message(role="user", content=multimodal_content)
    
    config = LLMConfig(model="model-1")
    payload = provider._build_payload([msg1, msg2], config)
    
    messages = payload["messages"]
    assert len(messages) == 2
    
    # Standard message should remain untouched
    assert messages[0] == {"role": "user", "content": "Hello, world!"}
    
    # Multimodal message should be successfully unpacked into OpenAI-compatible format
    assert messages[1]["role"] == "user"
    content = messages[1]["content"]
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0] == {"type": "text", "text": "Describe this image"}
    assert content[1] == {"type": "image_url", "image_url": {"url": "https://example.com/test.png"}}

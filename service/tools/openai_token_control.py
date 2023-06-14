import tiktoken

MAX_RANGES = 10


def discard_overlimit_messages(messages: list, model: str, max_token: int) -> list:
    """
    Discards messages that exceed the maximum number of tokens allowed by OpenAI.
    """
    range_count = 0
    while True:
        # 如果消息太少，就不处理
        if len(messages) <= 2:
            return messages

        # 防止意外(例如num_tokens_from_messages的实现没有及时跟随openai更新)出现死循环
        if range_count > MAX_RANGES:
            return messages

        token_count = num_tokens_from_messages(messages, model=model)

        range_count += 1

        if token_count <= max_token:
            return messages
        else:
            # 去掉过去的一半消息，给回答留下足够空间
            # 通常来说问题比较短，回复比较长，如果只去掉最远的1、2条消息，可能会导致问题占了大部分token，比方说4090个
            # 在最大token只能有4096个的情况下，回复只能有6个token，这样就会导致回复被截断
            messages = messages[int(len(messages) / 2):]
            continue


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    if model.startswith("gpt-3.5"):
        tokens_per_message = 4
        tokens_per_name = -1
    elif model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        tokens_per_message = 4
        tokens_per_name = -1
        #raise NotImplementedError(
        #    f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


if __name__ == '__main__':
    print(num_tokens_from_string("test", "cl100k_base"))
    messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "test"}]
    print(num_tokens_from_messages(messages, "gpt-3.5-turbo-0301"))

    print(num_tokens_from_messages(messages, "gpt-4"))
    print(num_tokens_from_messages(messages, "gpt-3.5-turbo"))
    print(num_tokens_from_messages(messages, "gpt-3.5-turbo-16k"))

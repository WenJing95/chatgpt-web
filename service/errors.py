from enum import Enum


class Errors(Enum):
    SOMETHING_WRONG = "ChatGptWebServerError:SomethingWrong"
    SOMETHING_WRONG_IN_OPENAI_GPT_API = "ChatGptWebServerError:SomethingWrongInOpenaiGptApi"
    SOMETHING_WRONG_IN_OPENAI_MODERATION_API = "ChatGptWebServerError:SomethingWrongInOpenaiModerationApi"
    SOMETHING_WRONG_IN_OPENAI_WHISPER_API = "ChatGptWebServerError:SomethingWrongInOpenaiWhisperApi"
    SOMETHING_WRONG_IN_LOCAL_WHISPER = "ChatGptWebServerError:SomethingWrongInLocalWhisper"
    UNKNOWN_WHISPER_SETTING = "ChatGptWebServerError:UnknownWhisperSetting"
    NOT_COMPLY_POLICY = "ChatGptWebServerError:NotComplyPolicy"
    PROMPT_IS_EMPTY = "ChatGptWebServerError:PromptIsEmpty"

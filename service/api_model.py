class ApiModel:
    KNOWN_API_MODEL_NAMES = ["gpt-3.5-turbo-0301",
                             "gpt-4",
                             # "gpt-4-32k"
                             ]
    KNOWN_API_MODEL_MAX_TOKENS = {"gpt-3.5-turbo-0301": 4096,
                                  "gpt-4": 8000,
                                  # "gpt-4-32k": 32000
                                  }

    @classmethod
    def get_api_model_name(cls, api_model_name: str, default_api_model_name: str) -> str:
        return api_model_name if api_model_name in cls.KNOWN_API_MODEL_NAMES else default_api_model_name

    @classmethod
    def get_max_token(cls, api_model_name: str, default_max_token: int) -> int:
        return cls.KNOWN_API_MODEL_MAX_TOKENS.get(api_model_name, default_max_token)

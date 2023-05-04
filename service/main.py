import openai
import os
from os.path import abspath, dirname
from loguru import logger
from chatgpt_wapper import process
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from message_store import MessageStore
from whisper_wapper import process_audio_local, process_audio_api
import argparse
from api_model import ApiModel
import platform
from pathlib import Path

log_folder = os.path.join(abspath(dirname(__file__)), "log")
logger.add(os.path.join(log_folder, "{time}.log"), level="INFO")

DEFAULT_TIMEOUT_MS_STRING = "100000"
MIN_TIMEOUT_MS = 15000
DEFAULT_DB_SIZE = 100000
DEFAULT_API_MODEL = "gpt-3.5-turbo"
DEFAULT_MAX_TOKEN = 4096
CURRENT_OS = platform.system()
USE_LOCAL_WHISPER = True

current_file_path = Path(__file__).resolve()
base_directory = current_file_path.parent

AUDIO_TMP_PATH = base_directory / "audio_tmp"
LOCAL_WHISPER_MODEL_PATH = base_directory / "tools" / "local-whisper" / "model" / "ggml-tiny.bin"
LOCAL_WHISPER_BIN_PATH_LINUX = base_directory / "tools" / "local-whisper" / "linux" / "whisper.cpp-master" / "main"
LOCAL_WHISPER_BIN_PATH_WINDOWS = base_directory / "tools" / "local-whisper" / "windows" / "main.exe"

massage_store = MessageStore(db_path="message_store.json", table_name="chatgpt", max_size=DEFAULT_DB_SIZE)

app = FastAPI()

stream_response_headers = {
    "Content-Type": "application/octet-stream",
    "Cache-Control": "no-cache",
}


@app.post("/config")
async def config():
    return JSONResponse(content=dict(
        message=None,
        status="Success",
        data=dict(
            apiModel=API_MODEL,
            socksProxy=SOCKS_PROXY,
            timeoutMs=OPENAI_TIMEOUT * 1000,
        )
    ))


@app.post("/chat-process")
async def chat_process(request_data: dict):
    prompt = request_data["prompt"]
    options = request_data["options"]

    if 1 == request_data["memory"]:
        memory_count = 5
    elif 50 == request_data["memory"]:
        memory_count = 20
    else:
        memory_count = 999

    if 1 == request_data["top_p"]:
        top_p = 0.2
    elif 50 == request_data["top_p"]:
        top_p = 0.6
    else:
        top_p = 1

    answer_text = process(prompt, options, memory_count, top_p, MASSAGE_STORE, OPENAI_TIMEOUT, MAX_TOKEN,
                          model=API_MODEL)
    return StreamingResponse(content=answer_text, headers=stream_response_headers, media_type="text/event-stream")


@app.post("/audio-chat-process")
async def audio_chat_process(audio: UploadFile = File(...)):
    if USE_LOCAL_WHISPER:
        local_whisper_bin_path = LOCAL_WHISPER_BIN_PATH_LINUX if "Linux" == CURRENT_OS else LOCAL_WHISPER_BIN_PATH_WINDOWS

        prompt = process_audio_local(audio,
                                     audio_tmp_path=AUDIO_TMP_PATH,
                                     model_path=LOCAL_WHISPER_MODEL_PATH,
                                     local_whisper_bin_path=local_whisper_bin_path)
    else:
        prompt = process_audio_api(audio,
                                   timeout=OPENAI_TIMEOUT)

    return StreamingResponse(content=prompt, headers=stream_response_headers, media_type="text/event-stream")


def init_config():
    # 读取配置
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--openai_api_key', type=str, help='API key for OpenAI')
    parser.add_argument('--api_model', type=str, default="gpt-3.5-turbo",
                        help='OpenAI API model, default is gpt-3.5-turbo')
    parser.add_argument('--socks_proxy', type=str, default="",
                        help='Socks proxy, default is "", e.g. http://127.0.0.1:10808')
    parser.add_argument('--timeout_ms', type=str, default=DEFAULT_TIMEOUT_MS_STRING,
                        help="(Deprecate) Timeout for OpenAI API, default is '100000'")
    parser.add_argument('--openai_timeout_ms', type=str, default=DEFAULT_TIMEOUT_MS_STRING,
                        help="Timeout for OpenAI API, default is '100000'")
    parser.add_argument('--use_local_whisper', type=str, default='True',
                        help="Use local whisper or api whisper. local whisper is free, api whisper is best,"
                             " default is 'True'")
    parser.add_argument('--host', type=str, default="0.0.0.0", help='Host for server, default is 0.0.0.0')
    parser.add_argument('--port', type=str, default="3002", help="Port for server, default is '3002'")

    args = parser.parse_args()

    if not args.openai_api_key:
        err = "OpenAI API key is not found. use --openai_api_key to set it."
        logger.error(err)
        raise TypeError(err)
    openai_api_key = args.openai_api_key
    openai.api_key = args.openai_api_key

    input_api_model = args.api_model
    if not input_api_model:
        err = "API model is not found."
        logger.error(err)
        raise TypeError(err)

    if input_api_model not in ApiModel.KNOWN_API_MODEL_NAMES:
        warning = "Unknown Api model '{}'. Legal settings are {}, The system has automatically set it to {}".format(
            input_api_model,
            ApiModel.KNOWN_API_MODEL_NAMES,
            DEFAULT_API_MODEL
        )
        logger.warning(warning)

    api_model = ApiModel.get_api_model_name(input_api_model, DEFAULT_API_MODEL)
    max_token = ApiModel.get_max_token(api_model, DEFAULT_MAX_TOKEN)

    socks_proxy = args.socks_proxy
    if socks_proxy:
        logger.info("Socks proxy is enabled.")
        logger.info("Socks proxy is {}.".format(socks_proxy))
        openai.proxy = socks_proxy
    else:
        logger.info("Socks proxy is disabled.")

    if DEFAULT_TIMEOUT_MS_STRING != args.timeout_ms:
        logger.warning("The parameter '--timeout_ms' is deprecated, please use '--openai_timeout_ms' instead.")
        args.openai_timeout_ms = args.timeout_ms

    openai_timeout_ms = args.openai_timeout_ms or DEFAULT_TIMEOUT_MS_STRING

    if isinstance(openai_timeout_ms, str):
        try:
            openai_timeout_ms = int(openai_timeout_ms)
        except:
            openai_timeout_ms = DEFAULT_TIMEOUT_MS_STRING

    if openai_timeout_ms < MIN_TIMEOUT_MS:
        openai_timeout_ms = MIN_TIMEOUT_MS
        logger.warning(
            "OpenAI timeout is too short, the system has automatically set it to {openai_timeout_ms}(ms).".format(
                openai_timeout_ms=MIN_TIMEOUT_MS))

    openai_timeout = openai_timeout_ms / 1000

    # service_timeout_ms = args.service_timeout_ms or 100000
    # if isinstance(service_timeout_ms, str):
    #     try:
    #         service_timeout_ms = int(service_timeout_ms)
    #     except:
    #         service_timeout_ms = 100000

    # if service_timeout_ms < 15000:
    #     service_timeout_ms = 15000
    #     logger.warning("Service timeout is too short, the system has automatically set it to 15000(ms).")

    # service_timeout = service_timeout_ms / 1000

    # if openai_timeout_ms > service_timeout_ms:
    #     openai_timeout = service_timeout
    #     logger.warning(
    #         "OpenAI timeout is longer than service timeout, the system has automatically set it to the same as service timeout.")

    host = args.host or "0.0.0.0"
    port = args.port or 3002
    if isinstance(port, str):
        try:
            port = int(port)
        except:
            err = "Port must be a number."
            logger.error(err)
            raise TypeError(err)

    use_local_whisper = True if args.use_local_whisper in ['True', 'true'] else False

    AUDIO_TMP_PATH.mkdir(parents=True, exist_ok=True)

    return massage_store, openai_api_key, host, port, api_model, \
           max_token, socks_proxy, openai_timeout, use_local_whisper


if __name__ == "__main__":
    MASSAGE_STORE, OPENAI_API_KEY, HOST, PORT, API_MODEL, MAX_TOKEN, SOCKS_PROXY, OPENAI_TIMEOUT, USE_LOCAL_WHISPER = init_config()
    logger.info("OPENAI_API_KEY:{}".format(OPENAI_API_KEY))
    logger.info("HOST:{}".format(HOST))
    logger.info("PORT:{}".format(PORT))
    logger.info("API_MODEL:{}".format(API_MODEL))
    logger.info("MAX_TOKEN:{}".format(MAX_TOKEN))
    logger.info("SOCKS_PROXY:{}".format(SOCKS_PROXY))
    logger.info("OPENAI_TIMEOUT_MS:{}".format(OPENAI_TIMEOUT * 1000))
    logger.info("USE_LOCAL_WHISPER:{}".format(USE_LOCAL_WHISPER))

    logger.info("AUDIO_TMP_PATH:{}".format(AUDIO_TMP_PATH))

    uvicorn.run(app, host=HOST, port=PORT)

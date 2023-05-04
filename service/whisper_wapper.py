import openai
import subprocess
from backoff import on_exception, expo
from io import BytesIO
from typing import Optional
from fastapi import UploadFile
import concurrent.futures
import asyncio
import traceback
from loguru import logger
from errors import Errors
import shutil
from pathlib import Path
import uuid

def upload_file_to_file_obj(upload_file: UploadFile, file_obj: Optional[BytesIO] = None):
    if file_obj is None:
        file_obj = BytesIO()
    file_obj.write(upload_file.file.read())
    file_obj.seek(0)
    file_obj.name = upload_file.filename
    return file_obj


async def process_audio_api(audio, timeout, model="whisper-1"):
    try:
        file = upload_file_to_file_obj(audio)

        params = dict(
            model=model,
            file=file,
            request_timeout=timeout,
        )
        func = _create
        transcript = await _create_async(params, func)
        if transcript is None:
            yield Errors.SOMETHING_WRONG_IN_OPENAI_WHISPER_API.value
            return

        prompt = transcript["text"]
        logger.debug("audio prompt: {}".format(prompt))
        del audio
        del file
    except:
        err = traceback.format_exc()
        logger.error(err)
        yield Errors.SOMETHING_WRONG.value
        return

    if not prompt:
        yield Errors.PROMPT_IS_EMPTY.value
        return

    yield "data: " + prompt


@on_exception(expo, openai.error.RateLimitError, max_tries=5)
def _create(params):
    return openai.Audio.transcribe(**params)


async def process_audio_local(audio, audio_tmp_path, model_path, local_whisper_bin_path):
    async def save_audio_file_to_disk(audio_file: UploadFile, path: Path):
        loop = asyncio.get_event_loop()
        with path.open("wb") as buffer:
            await loop.run_in_executor(None, shutil.copyfileobj, audio_file.file, buffer)
        audio_file.file.seek(0)

    def delete_file_if_exists(file_path: Path):
        if file_path.exists():
            file_path.unlink()

    filename = "{}.wav".format(str(uuid.uuid4()))
    file_path = audio_tmp_path / filename

    try:

        await save_audio_file_to_disk(audio, file_path)

        params = dict(
            file_path=file_path.as_posix(),
            model_path=model_path.as_posix(),
            local_whisper_bin_path=local_whisper_bin_path.as_posix(),
        )
        func = _local_create
        transcript = await _create_async(params, func)
        if transcript is None:
            yield Errors.SOMETHING_WRONG_IN_LOCAL_WHISPER.value
            return

        prompt = transcript["text"]
        logger.debug("audio prompt: {}".format(prompt))

        # remove leading newlines and spaces
        prompt = prompt.lstrip("\n ")

        if "[BLANK_AUDIO]" in prompt:
            prompt = ""
    except:
        err = traceback.format_exc()
        logger.error(err)
        yield Errors.SOMETHING_WRONG.value
        return
    finally:
        del audio
        delete_file_if_exists(file_path)

    if not prompt:
        yield Errors.PROMPT_IS_EMPTY.value
        return

    yield "data: " + prompt


def _local_create(params):
    args = [
        '--language', 'auto',
        '--model', params["model_path"],
        '-f', params["file_path"],
        '-nt',
    ]

    command = [params["local_whisper_bin_path"]] + args

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        logger.debug("Subprocess executed successfully.")
        logger.debug("Output:", result.stdout)
    else:
        logger.debug("Subprocess execution failed.")
        logger.debug("Error:", result.stderr)

    return {"text": result.stdout}


async def _create_async(params, func):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                executor, func, params
            )
        except:
            err = traceback.format_exc()
            logger.error(err)
            return None
    return result

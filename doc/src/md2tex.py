import functools
import subprocess
from hashlib import md5

import PIL.Image
from globals import *
from panflute import *
from yaml import Dumper, Loader, dump, load


def md2tex(md: str):
    """
    Use pandoc to convert markdown to latex
    """

    try:
        proc = subprocess.run(
            [
                "pandoc",
                "--from=markdown",
                "--to=latex",
                "--output=-",
                "--filter=" + str((file_dir / "md2tex.py").resolve()),
            ],
            input=md,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as e:
        logger.error(e)
        logger.error("Pandoc output:")
        logger.error(e.stdout)
        logger.error("Pandoc error:")
        logger.error(e.stderr)
        raise
    return proc.stdout


@functools.cache
def get_models():
    import torch
    from transformers import (
        AutoTokenizer,
        VisionEncoderDecoderModel,
        ViTFeatureExtractor,
    )

    logger.info("Loading models")
    model, feature_extractor, tokenizer = (
        f.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        for f in (VisionEncoderDecoderModel, ViTFeatureExtractor, AutoTokenizer)
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, feature_extractor, tokenizer, device


caption_cache_path = cache_dir / "captions.yaml"
caption_cache_path.touch(exist_ok=True)


@functools.cache
def get_caption_cache() -> dict:
    with open(caption_cache_path) as f:
        return load(f.read() or "{}", Loader=Loader)


def write_caption_cache(caption_cache: dict):
    with open(caption_cache_path, "w") as f:
        f.write(dump(caption_cache, Dumper=Dumper))


@functools.cache
def get_caption(image_path: str) -> str:
    image_path = Path(image_path)
    if not image_path.is_absolute():
        image_path = image_dir / image_path
    if not image_path.exists():
        logger.warning(f"Image {image_path} does not exist")
        return ""
    image = PIL.Image.open(image_path)

    hash = md5(image_path.read_bytes()).hexdigest()
    caption_cache = get_caption_cache()
    if (caption := caption_cache.get(hash)) is not None:
        return caption

    model, feature_extractor, tokenizer, device = get_models()
    if image.mode != "RGB":
        image = image.convert(mode="RGB")
    pixel_values = feature_extractor(
        images=[image], return_tensors="pt"
    ).pixel_values.to(device)
    predictions = tokenizer.batch_decode(
        model.generate(pixel_values, max_length=16, num_beams=4),
        skip_special_tokens=True,
    )
    caption_cache[hash] = (caption := predictions[0].strip())
    write_caption_cache(caption_cache)
    return caption


def filter(e, doc, language: str = "cpp"):
    match e:
        # use minted
        case Code():
            prefix = f"\\mintinline{{{language}}}"
            text = e.text
            if "!" not in text:
                prefix += "!" + text + "!"
            elif "|" not in text:
                prefix += "|" + text + "|"
            elif text.count("{") == text.count("}"):
                prefix += "{" + text + "}"
            else:
                raise RuntimeError(f'Unable to parse code block "{text}"')
            return RawInline(prefix, format="latex")
        case CodeBlock():
            try:
                language = e.classes[0]
            except IndexError:
                language = language
            return RawBlock(
                (f"\\begin{{minted}}{{{language}}}\n" f"{e.text}\n" f"\\end{{minted}}"),
                format="latex",
            )
        # image
        case Image():
            caption: str = stringify(e.content).strip().capitalize()
            if not caption:
                logger.warning(f"Image {e.url} has no caption")
                caption = get_caption(e.url).capitalize()
                logger.info(f"Generated caption: {caption}")
            label = e.attributes.get("label", "")
            label = "\\label{" + label + "}" if label else ""
            formats = ""

            attributes = {
                k: v.strip().removesuffix(",") for k, v in e.attributes.items()
            }
            if (width := attributes.get("width")) is not None:
                if width.endswith("%"):
                    width = int(width.removesuffix("%")) / 100
                    width = f"{width}\\linewidth"
                formats += f"width={width},"
            if (height := attributes.get("height")) is not None:
                if height.endswith("%"):
                    height = int(height.removesuffix("%")) / 100
                    height = f"{height}\\textheight"
                formats += f"height={height},"
            formats = formats.removesuffix(",")
            if formats:
                formats = f"[{formats}]"

            return RawInline(
                (
                    f"\\begin{{figure}}[H]\n"
                    f"\\centering\n"
                    f"\\img{formats}{{{e.url}}}\n"
                    f"\\caption{{{caption}}}{label}\n"
                    f"\\end{{figure}}"
                ),
                format="latex",
            )


def main(doc=None):
    return run_filter(filter, doc=doc)


if __name__ == "__main__":
    main()

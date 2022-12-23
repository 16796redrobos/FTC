import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Literal

from globals import *
from md2tex import md2tex
from tqdm import tqdm
from yaml import Loader, load


class CommandBuilder:
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.args: list[tuple[Literal("optional", "required"), str]] = []

    def required(self, arg: str):
        self.args.append(("required", arg))
        return self

    def optional(self, arg: str):
        self.args.append(("optional", arg))
        return self

    def optional_if(self, arg: str, condition: bool):
        if condition:
            self.optional(arg)
        return self

    def required_if(self, arg: str, condition: bool):
        if condition:
            self.required(arg)
        return self

    def __repr__(self):
        return (
            "\\"
            + self.cmd
            + "".join(
                f"[{arg}]" if opt == "optional" else f"{{{arg}}}"
                for opt, arg in self.args
            )
        )


def convert_time(time: str) -> str:
    """
    Convert a time string, either in 24-hour or 12-hour format, to a 12-hour format
    """
    result: str
    if re.match(r"^\d{1,2}:\d{2}$", time):
        result = datetime.strptime(time, "%H:%M").strftime("%-I:%M %p")
    else:
        time = re.sub(r"(\d{1,2}):(\d{2})\s*([AP]M)", r"\1:\2 \3", time)
        result = datetime.strptime(time, "%I:%M %p").strftime("%-I:%-M %p")
    return result


def convert_date(date: str) -> str:
    """
    Convert a date string to a date string.
    """
    return datetime.strptime(date, "%Y-%m-%d").strftime("%B %-d, %Y")


def convert_list(l: list) -> str:
    """
    Convert a list of string to a string.
    """

    l = [str(i) for i in l]
    if len(l) == 1:
        return l[0]
    elif len(l) == 2:
        return f"{l[0]} and {l[1]}"
    else:
        return ", ".join(l[:-1]) + f", and {l[-1]}"


def convert_name(m: list | str) -> str:
    return convert_list(m) if isinstance(m, list) else m


def itemizer(l: list) -> str:
    """
    Convert a list of string tp \itemize environment
    """

    return (
        "\\begin{itemize}\n"
        + "\n".join((r"\item " + i).strip() for i in l)
        + "\n\\end{itemize}"
    )


def enumerater(l: list) -> str:
    """
    Convert a list of string tp \enumerate environment
    """

    return (
        "\\begin{enumerate}\n"
        + "\n".join((r"\item " + i).strip() for i in l)
        + "\n\\end{enumerate}"
    )


def render_work_meet(content: Path) -> str:
    result = []
    with open(content) as f:
        data = load(f.read(), Loader=Loader)
    result.append(
        Template(r"\meeting{$date}{$duration}").substitute(
            date=convert_date(content.stem),
            duration="--".join(convert_time(data["time"][e]) for e in ["start", "end"]),
        )
    )
    subsection = lambda *args, **kwargs: Template(
        "\\subsection{$title}\n\n$body"
    ).substitute(*args, **kwargs)

    result.append(
        subsection(
            title="Attendees",
            body=convert_list(data["members"]),
        )
    )
    result.append(
        subsection(
            title="Goal",
            body=itemizer(md2tex(x) for x in data["goal"]),
        )
    )
    result.append(
        subsection(
            title="Overview",
            body=(
                md2tex(overview)
                if isinstance(overview := data["description"], str)
                else "\n\n".join(
                    repr(
                        CommandBuilder("work")
                        .required(convert_name(e["name"]))
                        .optional(e.get("title") or "NULL")
                        .optional_if("0pt", i == 0)
                    )
                    + "\n"
                    + md2tex(e["description"])
                    for i, e in enumerate(overview)
                )
            ),
        )
    )
    if struggles := data.get("struggles"):
        result.append(
            subsection(
                title="Struggles",
                body="\n\n".join(
                    Template(
                        "\\begin{struggle}\n"
                        "$problem\n"
                        "\\tcblower\n\n"
                        "$solution"
                        "\\end{struggle}\n"
                    ).substitute(
                        problem=md2tex(e["description"]),
                        solution=md2tex(e["solution"]),
                    )
                    for e in struggles
                ),
            )
        )
    result.append(
        subsection(
            title="Reflection",
            body=md2tex(data["reflection"]),
        )
    )
    return "\n\n".join(result) + "\\newpage"


def main():
    shutil.copy(
        template_dir / "main.tex",
        build_dir / "main.tex",
    )

    logbook = build_dir / "logbook.tex"
    with open(logbook, "w") as f:
        for entry in (
            pbar := tqdm(
                sorted(list((doc_dir / "log" / "work_meet").glob("*.yml"))),
                desc="Rendering logbook",
            )
        ):
            pbar.set_postfix_str(entry.stem)
            f.write(render_work_meet(entry) + "\n\n")


if __name__ == "__main__":
    main()

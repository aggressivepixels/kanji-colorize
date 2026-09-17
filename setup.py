from setuptools import setup, find_packages

setup(
    name="KanjiColorizer",
    version="0.12",
    description="Script and module to create colored stroke order diagrams based on KanjiVG data",
    author="Cayenne",
    author_email="cayennes@gmail.com",
    url="http://github.com/cayennes/kanji-colorize",
    packages=find_packages(exclude=["anki*"]),
    package_data={
        "kanjicolorizer": ["data/kanjivg/kanji/*.svg"],
    },
    scripts=["kanji_colorize"],
)

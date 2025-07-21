from setuptools import setup

setup(
    name="telegram-bot-curriculo",
    version="1.0.0",
    py_modules=["bot_curriculo"],
    install_requires=[
        "python-telegram-bot==20.0",
        "fpdf2",
    ],
)

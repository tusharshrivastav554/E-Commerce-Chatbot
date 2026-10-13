from setuptools import find_packages, setup

setup(
    name="Ecommercebot",
    version="0.0.1",
    author="tusharshrivastav554",
    author_email="tusharshrivastav554@gmail.com",
    packages=find_packages(),
    install_requires=['langchain-community','langchain','langchain-google-genai','google-generativeai','datasets','pypdf','python-dotenv','flask','supabase']
)

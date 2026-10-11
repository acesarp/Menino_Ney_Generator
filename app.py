import hmac
import logging
import os
import uuid
from base64 import b64decode
from datetime import datetime

import openai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Locally the keys come from .env; in Docker they come from compose's env_file.
load_dotenv()

MODEL = "gpt-image-2-2026-04-21"
DEFAULT_PROMPT = (
    "Coloque o Neymar nessa foto sem alterar as características originais da imagem, "
    "apenas adicione o Menino Ney na foto."
)
GENERATED_DIR = "generated"

logger = logging.getLogger("meninoney")

st.set_page_config(page_title="Menino Ney Generator", page_icon="⚽", layout="centered")


def check_password() -> bool:
    """Gate the app behind APP_PASSWORD, since every generation is billed to the OpenAI account.
    When APP_PASSWORD is not set, the app is open."""
    password = os.getenv("APP_PASSWORD")
    if not password or st.session_state.get("authenticated"):
        return True

    with st.form("login"):
        typed = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if hmac.compare_digest(typed.encode(), password.encode()):
                st.session_state.authenticated = True
                st.rerun()
            st.error("Senha incorreta.")
    return False


api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Chave da OpenAI não encontrada.")
    st.info("Defina OPENAI_API_KEY no arquivo `.env` na raiz do projeto.")
    st.stop()

st.title("⚽ Menino Ney Generator")

if not check_password():
    st.stop()

client = OpenAI(api_key=api_key)

st.write("Envie uma foto e o Menino Ney aparece nela, gerado pela OpenAI.")

uploaded_file = st.file_uploader("Escolha uma foto", type=["jpg", "jpeg", "png"])
prompt = st.text_area("O que fazer na foto", DEFAULT_PROMPT)

if uploaded_file is not None:
    st.image(uploaded_file, caption="Foto enviada")

if st.button("Gerar", type="primary", disabled=uploaded_file is None):
    with st.spinner("Gerando a imagem, pode levar até um minuto..."):
        try:
            response = client.images.edit(
                model=MODEL,
                # The upload is sent straight from memory, so visitors' photos are never stored.
                image=(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type),
                prompt=prompt,
            )
        except openai.AuthenticationError:
            logger.exception("OpenAI rejected the API key")
            st.error("A chave da OpenAI é inválida ou foi revogada.")
        except openai.RateLimitError:
            logger.exception("OpenAI rate limit or quota reached")
            st.error("Limite de uso da OpenAI atingido. Tente de novo mais tarde.")
        except openai.BadRequestError as error:
            # Usually the safety filter refusing the prompt or the image.
            logger.exception("OpenAI refused the request")
            st.error(f"A OpenAI recusou o pedido: {error.message}")
        except openai.OpenAIError:
            logger.exception("OpenAI request failed")
            st.error("Não foi possível gerar a imagem. Tente de novo.")
        else:
            image_bytes = b64decode(response.data[0].b64_json)
            # Saved once, here, and not on every rerun of the script.
            os.makedirs(GENERATED_DIR, exist_ok=True)
            file_name = f"menino_ney_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.png"
            with open(os.path.join(GENERATED_DIR, file_name), "wb") as f:
                f.write(image_bytes)
            st.session_state.result = image_bytes
            st.session_state.result_name = file_name

if "result" in st.session_state:
    st.success("Pronto!")
    st.image(st.session_state.result)
    st.download_button(
        "Baixar imagem",
        st.session_state.result,
        file_name=st.session_state.result_name,
        mime="image/png",
    )

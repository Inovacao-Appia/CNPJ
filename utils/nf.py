import base64
import multiprocessing
import os
import pdfplumber
import json
import streamlit as st
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from io import BytesIO
from openai import OpenAI

from utils.config import cfg

PROMPT_NF = """Você é um especialista financeiro e assistente de extração de dados.
Sua tarefa é extrair informações da Nota Fiscal e retornar EXCLUSIVAMENTE um objeto JSON válido.
Chaves obrigatórias: numero_nota, data_emissao, nome_prestador, valor_bruto, valor_liquido, descricao_servico, vencimento_boleto, numero_pedido"""

# Ver utils/contratos.py: extração de PDF é CPU-bound e, no processo do Streamlit,
# prende o GIL e trava as outras sessões/usuários numa NF grande. Roda em processo
# separado pelo mesmo motivo. mp_context="spawn": ver comentário equivalente em
# utils/contratos.py — evita cada worker herdar (fork) a memória inteira do processo
# do Streamlit, que já sozinho pode estourar o limite de memória do container.
_executor = None

# pdfplumber não faz OCR: página escaneada/imagem volta sem texto. Renderiza essa
# página como imagem e manda pro gpt-4o-mini (que já é multimodal) ler diretamente.
_RESOLUCAO_IMAGEM_PAGINA = 150


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"))
    return _executor


def _submeter(fn, *args):
    """Ver utils/contratos.py: se um worker morrer, o pool fica inutilizável até
    reiniciar o container — recria e tenta mais uma vez."""
    global _executor
    try:
        return _get_executor().submit(fn, *args).result()
    except BrokenProcessPool:
        _executor = None
        return _get_executor().submit(fn, *args).result()


def _get_client():
    api_key = cfg("OPENAI_API_KEY")
    if not api_key:
        st.error("Chave OPENAI_API_KEY não configurada. Adicione em Settings → Secrets no Streamlit Cloud.")
        st.stop()
    return OpenAI(api_key=api_key)


def _extrair_texto_pdf_worker(path):
    texto = ""
    paginas_sem_texto = []
    imagens_paginas = []
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(pdf.pages, start=1):
            t = p.extract_text()
            if t:
                texto += t + "\n"
            else:
                paginas_sem_texto.append(f"p.{i}")
                buffer = BytesIO()
                p.to_image(resolution=_RESOLUCAO_IMAGEM_PAGINA).original.save(buffer, format="PNG")
                imagens_paginas.append((f"PÁGINA {i}", base64.b64encode(buffer.getvalue()).decode()))
    return texto, paginas_sem_texto, imagens_paginas


def extrair_texto_pdf(path):
    """Retorna (texto, paginas_sem_texto, imagens_paginas). paginas_sem_texto/imagens_paginas
    cobrem páginas escaneadas/imagem — ver comentário acima de _RESOLUCAO_IMAGEM_PAGINA."""
    return _submeter(_extrair_texto_pdf_worker, path)


def analisar_nf(texto, imagens_paginas=None):
    client = _get_client()
    conteudo_usuario = [{"type": "text", "text": f"Texto extraído do PDF:\n{texto}"}]
    for rotulo_pagina, imagem_base64 in imagens_paginas or []:
        conteudo_usuario.append(
            {"type": "text", "text": f"Imagem da {rotulo_pagina} (sem texto extraível — leia como imagem):"}
        )
        conteudo_usuario.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{imagem_base64}"}}
        )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT_NF},
            {"role": "user", "content": conteudo_usuario},
        ],
    )
    return json.loads(response.choices[0].message.content)


def _demo():
    """Confirma que a extração de PDF roda num processo separado do principal —
    é essa separação que evita travar outras sessões numa NF grande."""
    pid_worker = _get_executor().submit(os.getpid).result()
    assert pid_worker != os.getpid(), "extração deveria rodar em processo separado, não no processo principal"
    print("ok: extração de PDF roda em processo separado")


if __name__ == "__main__":
    _demo()

import psycopg2
import psycopg2.extras
import streamlit as st
from psycopg2 import sql

from utils.config import cfg
from utils.contratos import COLUMNS


def _get_conn():
    dsn = cfg("DATABASE_URL")
    if not dsn:
        return None
    return psycopg2.connect(dsn)


def registrar_nf(arquivo: str, dados: dict, status: str = "sucesso", erro: str = None):
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs_nf
                    (arquivo, num_nota, data_emissao, prestador, valor_bruto, valor_liquido, status, erro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    arquivo,
                    dados.get("numero_nota"),
                    dados.get("data_emissao"),
                    dados.get("nome_prestador"),
                    str(dados.get("valor_bruto", "")),
                    str(dados.get("valor_liquido", "")),
                    status,
                    erro,
                ),
            )
    except Exception as e:
        st.warning(f"Falha ao registrar log: {e}")
    finally:
        conn.close()


def buscar_logs() -> list[dict]:
    conn = _get_conn()
    if not conn:
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM logs_nf ORDER BY timestamp DESC")
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def registrar_contrato(nome_grupo: str, arquivos: list[str], dados: dict, status: str = "sucesso", erro: str = None):
    conn = _get_conn()
    if not conn:
        return
    try:
        registro = {chave: dados.get(chave) for chave, _rotulo in COLUMNS}
        registro.update({
            "arquivo": nome_grupo,
            "arquivos_origem": ", ".join(arquivos),
            "status": status,
            "erro": erro,
        })
        colunas = list(registro.keys())
        query = sql.SQL("INSERT INTO logs_contratos ({}) VALUES ({})").format(
            sql.SQL(", ").join(map(sql.Identifier, colunas)),
            sql.SQL(", ").join([sql.Placeholder()] * len(colunas)),
        )
        with conn, conn.cursor() as cur:
            cur.execute(query, [registro[c] for c in colunas])
    except Exception as e:
        st.warning(f"Falha ao registrar log: {e}")
    finally:
        conn.close()


def buscar_logs_contratos() -> list[dict]:
    conn = _get_conn()
    if not conn:
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM logs_contratos ORDER BY timestamp DESC")
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

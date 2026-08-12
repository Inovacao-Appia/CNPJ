import psycopg2.extras
import streamlit as st

from utils.config import get_db_conn


def buscar_usuario(email: str) -> dict | None:
    conn = get_db_conn()
    if not conn or not email:
        return None
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM usuarios WHERE lower(email) = lower(%s)", (email,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def listar_usuarios(busca: str = "") -> list[dict]:
    conn = get_db_conn()
    if not conn:
        return []
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if busca:
                cur.execute(
                    "SELECT * FROM usuarios WHERE email ILIKE %s OR nome ILIKE %s ORDER BY email",
                    (f"%{busca}%", f"%{busca}%"),
                )
            else:
                cur.execute("SELECT * FROM usuarios ORDER BY email")
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def salvar_usuario(email: str, nome: str, role: str, ativo: bool):
    conn = get_db_conn()
    if not conn:
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (email, nome, role, ativo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                    SET nome = EXCLUDED.nome, role = EXCLUDED.role, ativo = EXCLUDED.ativo
                """,
                (email.strip().lower(), nome, role, ativo),
            )
    except Exception as e:
        st.warning(f"Falha ao salvar usuário {email}: {e}")
    finally:
        conn.close()


def excluir_usuario(email: str):
    conn = get_db_conn()
    if not conn:
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios WHERE lower(email) = lower(%s)", (email,))
    except Exception as e:
        st.warning(f"Falha ao remover usuário {email}: {e}")
    finally:
        conn.close()

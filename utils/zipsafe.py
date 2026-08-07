import os
import zipfile

_MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024  # ponytail: limite fixo simples, ajustar se lotes maiores forem legítimos


def extrair_zip_seguro(zip_path: str, dest_dir: str) -> None:
    """Extrai um .zip para dest_dir, rejeitando entradas que escapem do diretório
    (zip slip / path traversal) ou que estourem um limite de tamanho (zip bomb)."""
    dest_real = os.path.realpath(dest_dir)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        total = sum(m.file_size for m in zip_ref.infolist())
        if total > _MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Arquivo ZIP excede o tamanho máximo permitido.")

        for member in zip_ref.infolist():
            destino = os.path.realpath(os.path.join(dest_dir, member.filename))
            if destino != dest_real and not destino.startswith(dest_real + os.sep):
                raise ValueError(f"Entrada suspeita no ZIP ignorada: {member.filename}")
            zip_ref.extract(member, dest_dir)

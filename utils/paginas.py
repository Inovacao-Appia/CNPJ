"""Registro único das páginas controláveis da app — fonte única de verdade usada
tanto pelo menu (Home.py, via st.navigation) quanto pela matriz de acesso por
usuário (views/6_Administracao.py). Adicionar uma página nova aqui é o suficiente
pra ela aparecer no menu e na matriz.

Os arquivos ficam em views/, não em pages/: uma pasta chamada "pages" é
auto-registrada pelo Streamlit como rotas clássicas de multipage, acessíveis
direto por URL e SEM passar pelo Home.py (nem pelo require_login() de lá) —
isso ignoraria login e a própria matriz de acesso. Chamando de "views/" essa
rota automática não existe; tudo passa só pelo st.navigation() do Home.py.

PAGINA_ADMIN fica fora da matriz por usuário: é controlada só pelo papel (role
"admin"), não por paginas_bloqueadas — é a mesma regra que já existia."""

PAGINAS = [
    {"key": "consulta_cnpj", "path": "views/1_Consulta_CNPJ.py", "title": "Consulta CNPJ", "icon": "🔍"},
    {"key": "leitor_nf", "path": "views/2_Leitor_NF.py", "title": "Leitor de NF", "icon": "📄"},
    {"key": "logs_nf", "path": "views/3_Logs_NF.py", "title": "Logs de NF", "icon": "📊"},
    {"key": "leitor_contratos", "path": "views/4_Leitor_Contratos.py", "title": "Leitor de Contratos", "icon": "📑"},
    {"key": "logs_contratos", "path": "views/5_Logs_Contratos.py", "title": "Logs de Contratos", "icon": "📊"},
]

PAGINA_ADMIN = {"key": "administracao", "path": "views/6_Administracao.py", "title": "Administração", "icon": "🔐"}

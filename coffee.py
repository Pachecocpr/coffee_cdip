import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import json
import os
import base64
import urllib.parse
import unicodedata
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão Café Coletivo - NextGen Office", 
    page_icon="☕", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURAÇÃO DE BANCO, PASTA DE COMPROVANTES E IMAGEM ---
DB_FILE = "cafe_coletivo.db"
ARQUIVO_CONFIG = "config_pix.json"
PASTA_COMPROVANTES = "comprovantes"
NOME_IMAGEM_LOCAL = "capa.jpg"
URL_RESERVA_CAPA = "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?q=80&w=1200&auto=format&fit=crop"

if not os.path.exists(PASTA_COMPROVANTES):
    os.makedirs(PASTA_COMPROVANTES)

def obter_bg_css():
    """Converte a imagem local para Base64 para usar no CSS de fundo ou usa a URL reserva."""
    if os.path.exists(NOME_IMAGEM_LOCAL):
        with open(NOME_IMAGEM_LOCAL, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/jpeg;base64,{encoded_string}"
    return URL_RESERVA_CAPA

bg_url = obter_bg_css()

# --- VERIFICAÇÃO DE ESTADO PARA AJUSTAR A OPACIDADE DO FUNDO ---
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

eh_autenticado = st.session_state["usuario_logado"] is not None
overlay_opacity = "rgba(10, 14, 23, 0.92), rgba(15, 23, 42, 0.95)" if eh_autenticado else "rgba(10, 14, 23, 0.25), rgba(15, 23, 42, 0.40)"

# --- APLICAÇÃO DE CSS DINÂMICO (DARK NEON TECH) ---
st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    button[data-testid="stHeaderIconButton"] {{
        color: #00F0FF !important;
        background-color: rgba(0, 240, 255, 0.1) !important;
        border: 1px solid #00F0FF !important;
        border-radius: 8px !important;
    }}

    .stApp {{
        background: linear-gradient({overlay_opacity}), url('{bg_url}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        font-family: 'Segoe UI', Roboto, sans-serif !important;
        color: #E2E8F0 !important;
    }}

    div[data-testid="stForm"] {{
        background: rgba(10, 14, 23, 0.90) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 240, 255, 0.15) !important;
        backdrop-filter: blur(12px) !important;
    }}

    div[data-testid="stExpander"], div.stContainer {{
        background: rgba(15, 23, 42, 0.90) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        border: 1px solid rgba(0, 240, 255, 0.25) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 240, 255, 0.12) !important;
        backdrop-filter: blur(12px) !important;
    }}

    h1, h2, h3 {{
        color: #00F0FF !important;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.5) !important;
        font-weight: 700 !important;
    }}

    .login-title {{
        text-align: center;
        color: #00F0FF;
        font-size: 26px;
        font-weight: bold;
        margin-bottom: 15px;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
    }}

    div[data-testid="stFormSubmitButton"] > button, .stButton > button {{
        background: linear-gradient(90deg, #00F0FF 0%, #7000FF 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.3) !important;
    }}

    div[data-testid="stFormSubmitButton"] > button:hover, .stButton > button:hover {{
        transform: scale(1.02) !important;
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.6) !important;
    }}

    section[data-testid="stSidebar"] {{
        background-color: rgba(13, 17, 23, 0.95) !important;
        border-right: 1px solid rgba(0, 240, 255, 0.2) !important;
        backdrop-filter: blur(10px) !important;
    }}

    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {{
        color: #CBD5E1 !important;
        font-weight: 600 !important;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(15, 23, 42, 0.90) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        box-shadow: 0 0 12px rgba(0, 240, 255, 0.15) !important;
    }}

    .stTextInput input, .stSelectbox select, .stNumberInput input {{
        background-color: #090D16 !important;
        color: #00F0FF !important;
        border-radius: 8px !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
    }}

    img {{
        border-radius: 12px !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- ESTRUTURA DO BANCO DE DADOS (SQLITE) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabela de Usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    perfil TEXT NOT NULL DEFAULT 'Usuário',
                    pontos INTEGER DEFAULT 0,
                    ativo INTEGER DEFAULT 1
                )''')

    # Tabela de Estoque
    c.execute('''CREATE TABLE IF NOT EXISTS estoque (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT UNIQUE NOT NULL,
                    categoria TEXT NOT NULL,
                    quantidade INTEGER DEFAULT 0,
                    unidade TEXT NOT NULL
                )''')

    # Tabela de Compras/Entradas Financeiras
    c.execute('''CREATE TABLE IF NOT EXISTS compras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    comprador_id INTEGER,
                    item TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    valor_total REAL NOT NULL,
                    FOREIGN KEY(comprador_id) REFERENCES usuarios(id)
                )''')

    # Tabela de Doações (Sem custo)
    c.execute('''CREATE TABLE IF NOT EXISTS doacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    doador_id INTEGER,
                    item TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    pontos_ganhos INTEGER NOT NULL,
                    FOREIGN KEY(doador_id) REFERENCES usuarios(id)
                )''')

    # Tabela de Consumo/Saídas do Estoque
    c.execute('''CREATE TABLE IF NOT EXISTS saidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    usuario_id INTEGER,
                    item TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    motivo TEXT DEFAULT 'Consumo Interno',
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                )''')

    # Tabela de Registros de Pagamento (Comprovantes do Rateio)
    c.execute('''CREATE TABLE IF NOT EXISTS pagamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    usuario_id INTEGER,
                    valor_pago REAL NOT NULL,
                    arquivo_comprovante TEXT NOT NULL,
                    status TEXT DEFAULT 'Pendente',
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
                )''')

    # Criar usuário Master inicial caso não exista
    c.execute("SELECT * FROM usuarios WHERE perfil = 'Master'")
    if not c.fetchone():
        senha_admin = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
                  ("Administrador Master", "admin@empresa.com", senha_admin, "Master"))
    
    conn.commit()
    conn.close()

    if not os.path.exists(ARQUIVO_CONFIG):
        config_inicial = {
            "tipo_chave": "E-mail",
            "chave_pix": "admin@empresa.com",
            "nome_recebedor": "GESTAO CAFE COLETIVO",
            "cidade_recebedor": "BELO HORIZONTE",
            "data_vencimento_rateio": datetime.now().strftime("%d/%m/%Y"),
            "valor_rateio_por_pessoa": 0.0
        }
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump(config_inicial, f)

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# --- FUNÇÕES DE UTILIDADE E CRIPTOGRAFIA ---
def remover_acentos(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join([c for c in sem_acento if c.isalnum() or c.isspace()]).strip()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_config():
    with open(ARQUIVO_CONFIG, "r") as f:
        config = json.load(f)
        if "tipo_chave" not in config:
            config["tipo_chave"] = "E-mail"
        if "data_vencimento_rateio" not in config:
            config["data_vencimento_rateio"] = datetime.now().strftime("%d/%m/%Y")
        if "valor_rateio_por_pessoa" not in config:
            config["valor_rateio_por_pessoa"] = 0.0
        return config

def salvar_config(config):
    with open(ARQUIVO_CONFIG, "w") as f:
        json.dump(config, f)

def formatar_data_br(data_str):
    """Garante que qualquer string de data seja exibida no padrão DD/MM/AAAA"""
    if not data_str:
        return "Não definida"
    try:
        if "-" in data_str:
            dt = datetime.strptime(data_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        return data_str
    except Exception:
        return data_str

# --- GERADOR PIX VALIDADOR OFICIAL EMV / BANCO CENTRAL ---
def calcular_crc16(payload):
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if (crc & 0x8000) != 0:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def gerar_payload_pix(chave, nome, cidade, valor=0.0, txid="***"):
    chave_limpa = str(chave).strip()
    nome_limpo = remover_acentos(nome)[:25].upper()
    cidade_limpa = remover_acentos(cidade)[:15].upper()

    if not nome_limpo:
        nome_limpo = "CAFE COLETIVO"
    if not cidade_limpa:
        cidade_limpa = "BELO HORIZONTE"

    valor_str = f"{valor:.2f}" if valor > 0 else ""

    gui = "0014br.gov.bcb.pix"
    key = f"01{len(chave_limpa):02d}{chave_limpa}"
    merchant_account = f"26{len(gui + key):02d}{gui}{key}"

    cat = "52040000"
    currency = "5303986"
    amount = f"54{len(valor_str):02d}{valor_str}" if valor > 0 else ""
    country = "5802BR"
    merchant_name = f"59{len(nome_limpo):02d}{nome_limpo}"
    merchant_city = f"60{len(cidade_limpa):02d}{cidade_limpa}"

    txid_str = f"05{len(txid):02d}{txid}"
    additional_data = f"62{len(txid_str):02d}{txid_str}"

    payload_sem_crc = (
        f"000201{merchant_account}{cat}{currency}{amount}{country}"
        f"{merchant_name}{merchant_city}{additional_data}6304"
    )

    crc = calcular_crc16(payload_sem_crc)
    return payload_sem_crc + crc

def obter_url_qr_code(texto):
    texto_encoded = urllib.parse.quote(texto)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={texto_encoded}"

# --- INICIALIZAÇÃO ---
init_db()
config_pix = carregar_config()

try:
    eh_convidado = st.query_params.get("modo") == "convidado"
except Exception:
    eh_convidado = False

# ==========================================
# 📱 VISÃO CONVIDADO (LINK EXTERNO / QR CODE)
# ==========================================
if eh_convidado:
    st.title("☕ Café Coletivo - Acesso Convidado")
    st.write("Seja bem-vindo! Caso deseje contribuir espontaneamente com o café do escritório, utilize a chave Pix abaixo.")
    
    col1, col2 = st.columns([1, 2])
    
    payload_pix = gerar_payload_pix(
        chave=config_pix["chave_pix"], 
        nome=config_pix.get("nome_recebedor", "CAFE COLETIVO"), 
        cidade=config_pix.get("cidade_recebedor", "BELO HORIZONTE")
    )
    url_qr = obter_url_qr_code(payload_pix)

    with col1:
        st.image(url_qr, width=220)
    with col2:
        st.subheader("📲 Pagamento via Pix")
        st.write(f"**Tipo de Chave:** {config_pix.get('tipo_chave', 'E-mail')}")
        st.write(f"**Chave Pix (Copiar):** `{config_pix['chave_pix']}`")
        st.write(f"**Titular:** {remover_acentos(config_pix.get('nome_recebedor', 'CAFE COLETIVO'))}")
        st.text_area("Copia e Cola Pix (Payload EMV):", payload_pix, height=100)

    st.divider()
    st.subheader("📦 Itens Disponíveis no Momento")
    conn = get_db_connection()
    df_est = pd.read_sql_query("SELECT item as Item, categoria as Categoria, CAST(quantidade AS INTEGER) as Qtd, unidade as Unidade FROM estoque WHERE quantidade > 0", conn)
    conn.close()
    
    if not df_est.empty:
        st.dataframe(df_est, use_container_width=True)
    else:
        st.info("Estoque atual indisponível no momento.")

# ==========================================
# 🔐 SISTEMA PRINCIPAL (AUTENTICADO)
# ==========================================
else:
    if not st.session_state["usuario_logado"]:
        _, col_login_box, _ = st.columns([1, 1.2, 1])

        with col_login_box:
            st.markdown('<div class="login-title">☕ Café Coletivo</div>', unsafe_allow_html=True)
            
            tab_login, tab_cadastro = st.tabs(["🔒 Entrar", "📝 Aderir ao Café"])

            with tab_login:
                with st.form("form_login"):
                    login_input = st.text_input("Login:")
                    senha_input = st.text_input("Senha:", type="password")
                    btn_entrar = st.form_submit_button("Acessar Painel")

                    if btn_entrar:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("SELECT id, nome, email, perfil, senha FROM usuarios WHERE (email = ? OR nome = ?) AND ativo = 1", (login_input, login_input))
                        user = c.fetchone()
                        conn.close()

                        if user and user[4] == hash_senha(senha_input):
                            st.session_state["usuario_logado"] = {
                                "id": user[0], "nome": user[1], "email": user[2], "perfil": user[3]
                            }
                            st.success(f"Bem-vindo(a), {user[1]}!")
                            st.rerun()
                        else:
                            st.error("Credenciais inválidas ou conta inativa.")

            with tab_cadastro:
                with st.form("form_cadastro"):
                    nome_cad = st.text_input("Nome Completo / Login:")
                    email_cad = st.text_input("E-mail Corporativo:")
                    senha_cad = st.text_input("Senha de Acesso:", type="password")
                    btn_cadastrar = st.form_submit_button("Confirmar Adesão")

                    if btn_cadastrar:
                        if nome_cad and email_cad and senha_cad:
                            try:
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, 'Usuário')",
                                          (nome_cad, email_cad, hash_senha(senha_cad)))
                                conn.commit()
                                conn.close()
                                st.success("Cadastro realizado! Acesse a aba 'Entrar'.")
                            except sqlite3.IntegrityError:
                                st.error("E-mail ou Login já cadastrado.")
                        else:
                            st.warning("Preencha todos os campos.")

    # --- PAINEL DO USUÁRIO / MASTER ---
    else:
        user = st.session_state["usuario_logado"]
        
        # Sidebar Menu
        st.sidebar.title("☕ Café Coletivo")
        st.sidebar.write(f"👤 **{user['nome']}**")
        st.sidebar.caption(f"Perfil: {user['perfil']}")

        if st.sidebar.button("🚪 Sair"):
            st.session_state["usuario_logado"] = None
            st.rerun()

        opcoes_menu = [
            "📊 Dashboard & Métricas", 
            "📦 Estoque Geral", 
            "☕ Consumo / Baixa de Item",
            "🛒 Informar Compra (Com Custo)", 
            "🎁 Registrar Bônus/Doação", 
            "🏆 Ranking de Doadores", 
            "💳 Chave Pix & Contribuição"
        ]
        
        if user["perfil"] in ["Master", "ADM"]:
            opcoes_menu.append("🛠️ Painel Master (Gestão)")

        opcao = st.sidebar.radio("Navegação", opcoes_menu)

        # ----------------------------------------------------
        # 1. DASHBOARD & MÉTRICAS
        # ----------------------------------------------------
        if opcao == "📊 Dashboard & Métricas":
            st.header("📊 Faturamento, Custos, Estoque e Rateio")
            
            conn = get_db_connection()
            total_investido = pd.read_sql_query("SELECT SUM(valor_total) as total FROM compras", conn)["total"].fillna(0).iloc[0]
            total_itens_estoque = int(pd.read_sql_query("SELECT SUM(quantidade) as total FROM estoque WHERE quantidade > 0", conn)["total"].fillna(0).iloc[0])
            total_doacoes = pd.read_sql_query("SELECT COUNT(*) as total FROM doacoes", conn)["total"].fillna(0).iloc[0]
            conn.close()

            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Investimento Total (Compras)", f"R$ {total_investido:.2f}")
            m2.metric("📦 Volume em Estoque (Un)", f"{total_itens_estoque}")
            m3.metric("🎁 Doações/Bônus Recebidos", f"{total_doacoes} registros")

            st.divider()

            # --- SEÇÃO VISUAL DE ARRECADAÇÃO E RATEIO ---
            st.subheader("👥 Gestão de Participantes - Status do Rateio")

            conn = get_db_connection()
            df_membros = pd.read_sql_query("SELECT id, nome, perfil FROM usuarios WHERE ativo = 1 AND perfil IN ('Master', 'ADM', 'Usuário')", conn)
            
            total_arrecadado_real = pd.read_sql_query("SELECT SUM(valor_pago) as total FROM pagamentos", conn)["total"].fillna(0).iloc[0]
            df_pags = pd.read_sql_query("SELECT DISTINCT usuario_id FROM pagamentos", conn)
            conn.close()

            data_venc_br = formatar_data_br(config_pix.get("data_vencimento_rateio", ""))

            pagos_ids = set(df_pags["usuario_id"].tolist())
            
            df_membros["Status"] = df_membros["id"].apply(lambda x: "🟢 Pago" if x in pagos_ids else "🔴 Pendente")

            qtd_pagos = len(df_membros[df_membros["Status"] == "🟢 Pago"])
            qtd_pendentes = len(df_membros[df_membros["Status"] == "🔴 Pendente"])
            total_membros_qtd = len(df_membros)

            saldo_restante = max(0.0, total_investido - total_arrecadado_real)
            valor_devido_por_pendente = round((saldo_restante / qtd_pendentes), 2) if qtd_pendentes > 0 else 0.00

            df_membros["Valor Devido (R$)"] = df_membros["id"].apply(
                lambda x: 0.00 if x in pagos_ids else valor_devido_por_pendente
            )

            c_part1, c_part2 = st.columns([1, 1.2])

            with c_part1:
                st.write(f"**Data Vencimento:** `{data_venc_br}`")
                st.metric("Total Arrecadado (Real)", f"R$ {total_arrecadado_real:.2f}", f"{qtd_pagos}/{total_membros_qtd} Pagos")
                if qtd_pendentes > 0:
                    st.caption(f"💡 Falta arrecadar: **R$ {saldo_restante:.2f}** (Dividido em R$ {valor_devido_por_pendente:.2f} p/ cada pendente)")
                else:
                    st.caption("🎉 Rateio 100% quitado por todos os membros!")

                df_graf_rateio = pd.DataFrame({
                    "Status": ["Pago", "Pendente"],
                    "Quantidade": [qtd_pagos, qtd_pendentes]
                })
                fig_rateio = px.pie(
                    df_graf_rateio, 
                    values="Quantidade", 
                    names="Status", 
                    hole=0.5,
                    color="Status",
                    color_discrete_map={"Pago": "#00F0FF", "Pendente": "#FF0055"},
                    template="plotly_dark"
                )
                fig_rateio.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=220)
                st.plotly_chart(fig_rateio, use_container_width=True)

            with c_part2:
                st.write("📋 **Lista de Transparência do Rateio:**")
                st.dataframe(
                    df_membros[["nome", "perfil", "Status", "Valor Devido (R$)"]]
                    .rename(columns={"nome": "Participante", "perfil": "Perfil"})
                    .style.format({"Valor Devido (R$)": "R$ {:.2f}"}),
                    use_container_width=True,
                    height=280
                )

            st.divider()

            conn = get_db_connection()
            df_compras = pd.read_sql_query("SELECT item, SUM(valor_total) as custo_total FROM compras GROUP BY item", conn)
            df_estoque = pd.read_sql_query("SELECT item, CAST(quantidade AS INTEGER) as quantidade FROM estoque WHERE quantidade > 0", conn)
            conn.close()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Investimento por Item")
                if not df_compras.empty:
                    fig_custo = px.pie(df_compras, values="custo_total", names="item", hole=0.4, template="plotly_dark")
                    st.plotly_chart(fig_custo, use_container_width=True)
                else:
                    st.info("Sem dados de compras.")

            with c2:
                st.subheader("Nível do Estoque Disponível")
                if not df_estoque.empty:
                    fig_est = px.bar(df_estoque, x="item", y="quantidade", color="quantidade", template="plotly_dark")
                    st.plotly_chart(fig_est, use_container_width=True)
                else:
                    st.info("Estoque vazio.")

        # ----------------------------------------------------
        # 2. ESTOQUE GERAL
        # ----------------------------------------------------
        elif opcao == "📦 Estoque Geral":
            st.header("📦 Controle do Estoque Atual")
            conn = get_db_connection()
            df_estoque = pd.read_sql_query("SELECT item as Item, categoria as Categoria, CAST(quantidade AS INTEGER) as Qtd, unidade as Unidade FROM estoque WHERE quantidade > 0", conn)
            conn.close()

            if not df_estoque.empty:
                st.dataframe(df_estoque, use_container_width=True)
            else:
                st.info("Não há itens com saldo disponível no estoque no momento.")

        # ----------------------------------------------------
        # 3. CONSUMO / BAIXA DE ITEM NO ESTOQUE
        # ----------------------------------------------------
        elif opcao == "☕ Consumo / Baixa de Item":
            st.header("☕ Registrar Consumo / Baixa do Estoque")
            st.write("Abriu um pó de café, usou um pacote de açúcar ou consumiu algum item? Registre a baixa aqui.")

            conn = get_db_connection()
            df_disponivel = pd.read_sql_query("SELECT item, CAST(quantidade AS INTEGER) as quantidade, unidade FROM estoque WHERE quantidade > 0", conn)
            conn.close()

            if not df_disponivel.empty:
                dict_itens = dict(zip(df_disponivel["item"], df_disponivel["quantidade"]))
                dict_unidades = dict(zip(df_disponivel["item"], df_disponivel["unidade"]))

                with st.form("form_baixa_estoque"):
                    item_selecionado = st.selectbox("Selecione o Item Consumido:", list(dict_itens.keys()))
                    qtd_disponivel = int(dict_itens[item_selecionado])
                    unidade_item = dict_unidades[item_selecionado]

                    st.info(f"Quantidade disponível em estoque: **{qtd_disponivel} {unidade_item}**")

                    qtd_consumida = st.number_input(
                        f"Quantidade Consumida ({unidade_item}):", 
                        min_value=1, 
                        max_value=qtd_disponivel, 
                        step=1
                    )
                    motivo_consumo = st.text_input("Motivo / Observação:", value="Consumo Interno / Uso da Equipe")

                    if st.form_submit_button("📉 Registrar Baixa no Estoque"):
                        conn = get_db_connection()
                        c = conn.cursor()

                        c.execute(
                            "INSERT INTO saidas (data_hora, usuario_id, item, quantidade, motivo) VALUES (?, ?, ?, ?, ?)",
                            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], item_selecionado, int(qtd_consumida), motivo_consumo)
                        )

                        c.execute(
                            "UPDATE estoque SET quantidade = quantidade - ? WHERE item = ?", 
                            (int(qtd_consumida), item_selecionado)
                        )

                        conn.commit()
                        conn.close()

                        st.success(f"Baixa de {int(qtd_consumida)} {unidade_item} de '{item_selecionado}' registrada com sucesso!")
                        st.rerun()
            else:
                st.warning("Não há itens disponíveis no estoque no momento.")

            st.divider()

            st.subheader("📋 Histórico de Consumo / Saídas Recentes")
            conn = get_db_connection()
            df_saidas = pd.read_sql_query("""
                SELECT s.data_hora as 'Data/Hora', u.nome as 'Usuário', s.item as 'Item', CAST(s.quantidade AS INTEGER) as 'Qtd Retirada', s.motivo as 'Motivo'
                FROM saidas s
                JOIN usuarios u ON s.usuario_id = u.id
                ORDER BY s.id DESC LIMIT 15
            """, conn)
            conn.close()

            if not df_saidas.empty:
                st.dataframe(df_saidas, use_container_width=True)
            else:
                st.info("Nenhuma saída registrada até o momento.")

        # ----------------------------------------------------
        # 4. INFORMAR COMPRA (COM CUSTO)
        # ----------------------------------------------------
        elif opcao == "🛒 Informar Compra (Com Custo)":
            st.header("🛒 Registrar Compra para o Café")
            st.write("Comprou algo para a equipe e usou o fundo/dinheiro próprio? Cadastre aqui.")

            with st.form("form_compra"):
                item_nome = st.text_input("Item (ex: Café Solúvel, Açúcar, Leite):")
                categoria = st.selectbox("Categoria:", ["Insumos Básicos", "Matinais", "Descartáveis", "Snacks"])
                qtd = st.number_input("Quantidade Comprada:", min_value=1, step=1)
                unidade = st.selectbox("Unidade:", ["Unidades", "Kg", "Pacotes", "Caixas", "Litros"])
                valor_total = st.number_input("Valor Total Pago (R$):", min_value=0.01, step=1.0)
                
                btn_salvar_compra = st.form_submit_button("Registrar Compra e Atualizar Estoque")

                if btn_salvar_compra:
                    if item_nome:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO compras (data_hora, comprador_id, item, quantidade, valor_total) VALUES (?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], item_nome, int(qtd), valor_total))
                        
                        c.execute("SELECT quantidade FROM estoque WHERE item = ?", (item_nome,))
                        res = c.fetchone()
                        if res:
                            c.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE item = ?", (int(qtd), item_nome))
                        else:
                            c.execute("INSERT INTO estoque (item, categoria, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                      (item_nome, categoria, int(qtd), unidade))
                        
                        conn.commit()
                        conn.close()
                        st.success("Compra registrada e estoque atualizado!")
                    else:
                        st.error("Informe o nome do item.")

        # ----------------------------------------------------
        # 5. REGISTRAR BÔNUS/DOAÇÃO (SEM CUSTO)
        # ----------------------------------------------------
        elif opcao == "🎁 Registrar Bônus/Doação":
            st.header("🎁 Doar Item Extra (Pontua no Ranking)")
            st.write("Trouxe algo de casa para compartilhar com o time sem pedir reembolso? Registre e receba pontos no ranking!")

            with st.form("form_doacao"):
                item_nome = st.text_input("Item Doador (ex: Bolo caseiro, Pó de café extra):")
                categoria = st.selectbox("Categoria:", ["Insumos Básicos", "Matinais", "Doces/Mimos", "Snacks"])
                qtd = st.number_input("Quantidade Doada:", min_value=1, step=1)
                unidade = st.selectbox("Unidade:", ["Unidades", "Kg", "Pacotes", "Litros"])
                
                btn_salvar_doacao = st.form_submit_button("Registrar Doação")

                if btn_salvar_doacao:
                    if item_nome:
                        pontos = int(qtd * 10)
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO doacoes (data_hora, doador_id, item, quantidade, pontos_ganhos) VALUES (?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], item_nome, int(qtd), pontos))
                        
                        c.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pontos, user["id"]))

                        c.execute("SELECT quantidade FROM estoque WHERE item = ?", (item_nome,))
                        res = c.fetchone()
                        if res:
                            c.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE item = ?", (int(qtd), item_nome))
                        else:
                            c.execute("INSERT INTO estoque (item, categoria, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                      (item_nome, categoria, int(qtd), unidade))

                        conn.commit()
                        conn.close()
                        st.balloons()
                        st.success(f"Obrigado pela doação! Você ganhou +{pontos} pontos no Ranking!")
                    else:
                        st.error("Informe o item doado.")

        # ----------------------------------------------------
        # 6. RANKING DE DOADORES
        # ----------------------------------------------------
        elif opcao == "🏆 Ranking de Doadores":
            st.header("🏆 Ranking de Colaboradores e Doadores")
            st.write("Membros que mais contribuíram com mimos e doações para o café da equipe:")

            conn = get_db_connection()
            df_ranking = pd.read_sql_query("SELECT nome as Colaborador, pontos as 'Pontos Acumulados' FROM usuarios WHERE pontos > 0 ORDER BY pontos DESC", conn)
            conn.close()

            if not df_ranking.empty:
                st.dataframe(df_ranking, use_container_width=True)
            else:
                st.info("Nenhuma doação registrada ainda. Seja o primeiro a pontuar!")

        # ----------------------------------------------------
        # 7. CHAVE PIX & CONTRIBUIÇÃO (COM CORREÇÃO DO MIN_VALUE)
        # ----------------------------------------------------
        elif opcao == "💳 Chave Pix & Contribuição":
            st.header("💳 Chave Pix Oficial e Rateio do Café Coletivo")

            conn = get_db_connection()
            total_compras = pd.read_sql_query("SELECT SUM(valor_total) as total FROM compras", conn)["total"].fillna(0).iloc[0]
            total_arrecadado_real = pd.read_sql_query("SELECT SUM(valor_pago) as total FROM pagamentos", conn)["total"].fillna(0).iloc[0]
            df_pendentes_cnt = pd.read_sql_query("SELECT COUNT(*) as total FROM usuarios WHERE ativo = 1 AND perfil IN ('Master', 'ADM', 'Usuário') AND id NOT IN (SELECT DISTINCT usuario_id FROM pagamentos)", conn)["total"].fillna(1).iloc[0]
            conn.close()

            data_venc_br = formatar_data_br(config_pix.get("data_vencimento_rateio", ""))
            saldo_restante = max(0.0, total_compras - total_arrecadado_real)
            valor_rateio_dinamico = round((saldo_restante / df_pendentes_cnt), 2) if df_pendentes_cnt > 0 else 0.00

            col_r1, col_r2 = st.columns(2)
            col_r1.metric("💰 Valor Devido Atual por Pendente", f"R$ {valor_rateio_dinamico:.2f}")
            col_r2.metric("📅 Data Limite de Pagamento", data_venc_br)

            st.divider()

            payload_pix = gerar_payload_pix(
                chave=config_pix["chave_pix"], 
                nome=config_pix.get("nome_recebedor", "CAFE COLETIVO"), 
                cidade=config_pix.get("cidade_recebedor", "BELO HORIZONTE"),
                valor=valor_rateio_dinamico
            )
            url_qr = obter_url_qr_code(payload_pix)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(url_qr, width=220)
            with col2:
                st.write(f"**Tipo de Chave:** {config_pix.get('tipo_chave', 'E-mail')}")
                st.write(f"**Chave Pix Registrada:** `{config_pix['chave_pix']}`")
                st.write(f"**Titular:** {remover_acentos(config_pix.get('nome_recebedor', 'CAFE COLETIVO'))}")
                st.text_area("Copia e Cola Pix (Payload EMV):", payload_pix, height=100)

            st.divider()

            st.subheader("📤 Registrar Pagamento / Anexar Comprovante")
            
            # Ajuste de segurança para o valor inicial do input
            valor_sugerido_input = float(valor_rateio_dinamico) if valor_rateio_dinamico > 0 else 0.00

            with st.form("form_comprovante"):
                valor_pago_input = st.number_input(
                    "Valor Pago (R$):", 
                    value=valor_sugerido_input, 
                    min_value=0.00, 
                    step=1.0
                )
                arquivo_enviado = st.file_uploader("Selecione o Comprovante (PNG, JPG ou PDF):", type=["png", "jpg", "jpeg", "pdf"])
                
                btn_enviar_comp = st.form_submit_button("📩 Enviar Comprovante de Pagamento")

                if btn_enviar_comp:
                    if valor_pago_input <= 0:
                        st.error("Informe um valor pago maior que zero.")
                    elif arquivo_enviado is not None:
                        extensao = arquivo_enviado.name.split(".")[-1]
                        nome_arquivo_salvo = f"comp_user_{user['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extensao}"
                        caminho_completo = os.path.join(PASTA_COMPROVANTES, nome_arquivo_salvo)

                        with open(caminho_completo, "wb") as f:
                            f.write(arquivo_enviado.getbuffer())

                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("INSERT INTO pagamentos (data_hora, usuario_id, valor_pago, arquivo_comprovante) VALUES (?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], valor_pago_input, nome_arquivo_salvo))
                        conn.commit()
                        conn.close()

                        st.success("Comprovante enviado com sucesso! O status do seu pagamento e os valores devidos já foram recalculados.")
                        st.rerun()
                    else:
                        st.error("Por favor, selecione um arquivo de comprovante.")

            st.divider()

            url_atual = st.context.headers.get("host", "localhost:8501")
            link_convidado = f"https://{url_atual}/?modo=convidado"
            st.subheader("📲 Link de Acesso Rápido / Visitante")
            st.code(link_convidado)

        # ----------------------------------------------------
        # 8. PAINEL MASTER / ADM
        # ----------------------------------------------------
        elif opcao == "🛠️ Painel Master (Gestão)" and user["perfil"] in ["Master", "ADM"]:
            st.header("🛠️ Administração do Sistema e Perfis")

            tab_users, tab_pix_cfg, tab_rateio, tab_limpeza = st.tabs([
                "👥 Controle de Usuários", 
                "⚙️ Configurações Pix", 
                "💰 Gestão de Rateio", 
                "🧹 Limpeza de Dados"
            ])

            with tab_users:
                conn = get_db_connection()
                df_users = pd.read_sql_query("SELECT id, nome as 'Nome/Login', email as 'E-mail', perfil as 'Perfil', ativo as 'Ativo' FROM usuarios", conn)
                conn.close()

                st.dataframe(df_users, use_container_width=True)

                st.subheader("Editar Dados do Usuário / Resetar Senha")
                
                user_dict = dict(zip(df_users["id"], df_users["Nome/Login"]))
                user_selected_id = st.selectbox("Selecione o Usuário:", list(user_dict.keys()), format_func=lambda x: f"ID {x} - {user_dict[x]}")

                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT nome, email, perfil FROM usuarios WHERE id = ?", (user_selected_id,))
                user_data = c.fetchone()
                conn.close()

                col_u1, col_u2, col_u3, col_u4 = st.columns(4)
                
                with col_u1:
                    novo_login = st.text_input("Novo Login / Nome:", value=user_data[0] if user_data else "")
                with col_u2:
                    novo_email = st.text_input("Novo E-mail:", value=user_data[1] if user_data else "")
                with col_u3:
                    novo_perfil = st.selectbox("Novo Perfil:", ["Usuário", "ADM", "Master", "Convidado"], index=["Usuário", "ADM", "Master", "Convidado"].index(user_data[2]) if user_data and user_data[2] in ["Usuário", "ADM", "Master", "Convidado"] else 0)
                with col_u4:
                    nova_senha = st.text_input("Nova Senha (deixe vazio para não alterar):", type="password")

                if st.button("Salvar Alterações do Usuário"):
                    try:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("UPDATE usuarios SET nome = ?, email = ?, perfil = ? WHERE id = ?", (novo_login, novo_email, novo_perfil, user_selected_id))
                        
                        if nova_senha:
                            c.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (hash_senha(nova_senha), user_selected_id))
                        
                        conn.commit()
                        conn.close()
                        st.success(f"Usuário ID {user_selected_id} atualizado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("O E-mail ou Login informado já pertence a outro usuário.")

            with tab_pix_cfg:
                st.subheader("⚙️ Alterar e Cadastrar Chave Pix")
                st.write("Informe **exclusivamente** o valor da chave no campo correspondente para evitar erros no QR Code.")

                tipos_pix = ["Telefone", "E-mail", "CPF / CNPJ", "Chave Aleatória (EVP)"]
                tipo_atual = config_pix.get("tipo_chave", "Telefone")
                idx_tipo = tipos_pix.index(tipo_atual) if tipo_atual in tipos_pix else 0

                with st.form("form_config_pix_admin"):
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        tipo_chave_sel = st.selectbox("Tipo de Chave Pix:", tipos_pix, index=idx_tipo)
                    with col_p2:
                        chave = st.text_input("Chave Pix (Ex: 31987121065 ou +5531987121065):", value=config_pix["chave_pix"])

                    col_p3, col_p4 = st.columns(2)
                    with col_p3:
                        nome = st.text_input("Nome do Titular Recebedor:", value=config_pix.get("nome_recebedor", "CELIO PACHECO RODRIGUES"))
                    with col_p4:
                        cidade = st.text_input("Cidade do Titular:", value=config_pix.get("cidade_recebedor", "BELO HORIZONTE"))

                    if st.form_submit_button("💾 Salvar Nova Chave Pix"):
                        chave_limpa = chave.strip()

                        if tipo_chave_sel == "Telefone":
                            apenas_num = "".join(filter(str.isdigit, chave_limpa))
                            if len(apenas_num) in [10, 11]:
                                chave_limpa = f"+55{apenas_num}"
                            elif len(apenas_num) in [12, 13] and apenas_num.startswith("55"):
                                chave_limpa = f"+{apenas_num}"

                        elif tipo_chave_sel == "CPF / CNPJ":
                            chave_limpa = "".join(filter(str.isdigit, chave_limpa))

                        config_pix["tipo_chave"] = tipo_chave_sel
                        config_pix["chave_pix"] = chave_limpa
                        config_pix["nome_recebedor"] = remover_acentos(nome)
                        config_pix["cidade_recebedor"] = remover_acentos(cidade)
                        salvar_config(config_pix)
                        
                        st.success(f"Chave Pix salva e validada com sucesso! Valor: '{chave_limpa}'")
                        st.rerun()

            with tab_rateio:
                st.subheader("💰 Calculadora de Rateio e Vencimento")

                conn = get_db_connection()
                total_compras = pd.read_sql_query("SELECT SUM(valor_total) as total FROM compras", conn)["total"].fillna(0).iloc[0]
                total_membros = pd.read_sql_query("SELECT COUNT(*) as total FROM usuarios WHERE ativo = 1 AND perfil IN ('Master', 'ADM', 'Usuário')", conn)["total"].fillna(1).iloc[0]
                conn.close()

                rateio_calculado = total_compras / total_membros if total_membros > 0 else 0.0

                c_rat1, c_rat2, c_rat3 = st.columns(3)
                c_rat1.metric("🛒 Total Acumulado em Compras", f"R$ {total_compras:.2f}")
                c_rat2.metric("👥 Total de Membros (Com Master/ADM)", f"{total_membros} pessoas")
                c_rat3.metric("🧮 Rateio Sugerido / Pessoa", f"R$ {rateio_calculado:.2f}")

                st.divider()

                with st.form("form_definir_rateio"):
                    st.write("Defina a **Data Limite de Vencimento** do rateio:")
                    
                    raw_data = config_pix.get("data_vencimento_rateio", "")
                    try:
                        if "/" in raw_data:
                            data_venc_atual = datetime.strptime(raw_data, "%d/%m/%Y").date()
                        else:
                            data_venc_atual = datetime.strptime(raw_data, "%Y-%m-%d").date()
                    except Exception:
                        data_venc_atual = datetime.now().date()

                    nova_data_venc = st.date_input("Data de Vencimento do Pagamento:", value=data_venc_atual, format="DD/MM/YYYY")

                    if st.form_submit_button("💾 Salvar Configurações do Rateio"):
                        config_pix["data_vencimento_rateio"] = nova_data_venc.strftime("%d/%m/%Y")
                        salvar_config(config_pix)
                        st.success("Data de vencimento salva com sucesso!")
                        st.rerun()

                st.divider()

                st.subheader("📥 Comprovantes Enviados pelos Membros")
                conn = get_db_connection()
                df_pagamentos = pd.read_sql_query("""
                    SELECT p.id, p.data_hora as 'Data/Hora', u.nome as 'Membro', p.valor_pago as 'Valor Pago', p.arquivo_comprovante as 'Arquivo'
                    FROM pagamentos p
                    JOIN usuarios u ON p.usuario_id = u.id
                    ORDER BY p.id DESC
                """, conn)
                conn.close()

                if not df_pagamentos.empty:
                    st.dataframe(df_pagamentos[["Data/Hora", "Membro", "Valor Pago", "Arquivo"]], use_container_width=True)

                    st.write("Selecione um registro para baixar o comprovante:")
                    pag_id_sel = st.selectbox("Selecione o Registro de Pagamento:", df_pagamentos["id"].tolist())
                    
                    row_pag = df_pagamentos[df_pagamentos["id"] == pag_id_sel].iloc[0]
                    caminho_arq = os.path.join(PASTA_COMPROVANTES, row_pag["Arquivo"])

                    if os.path.exists(caminho_arq):
                        with open(caminho_arq, "rb") as file:
                            btn = st.download_button(
                                label=f"⬇️ Baixar Comprovante de {row_pag['Membro']}",
                                data=file,
                                file_name=row_pag["Arquivo"]
                            )
                else:
                    st.info("Nenum comprovante enviado até o momento.")

            with tab_limpeza:
                st.subheader("🧹 Limpeza Seletiva de Dados (Apenas Usuário Master)")
                st.write("Marque abaixo quais módulos / bancos de dados você deseja zerar completamente:")

                col_limp1, col_limp2 = st.columns(2)

                with col_limp1:
                    limpar_compras = st.checkbox("🛒 **Histórico de Compras** (Registros de compras efetuadas com custo)")
                    limpar_saidas = st.checkbox("☕ **Histórico de Consumo/Saídas** (Registros de itens consumidos)")
                    limpar_pagamentos = st.checkbox("💳 **Histórico de Pagamentos e Comprovantes** (Pagamentos efetuados pelos membros)")

                with col_limp2:
                    limpar_doacoes = st.checkbox("🎁 **Doações e Ranking** (Histórico de doações e zerar pontos acumulados)")
                    limpar_estoque = st.checkbox("📦 **Estoque Atual** (Remove todos os itens cadastrados no estoque)")

                st.divider()
                confirmar_limpeza = st.checkbox("⚠️ **Confirmo a exclusão definitiva dos dados selecionados acima.**")

                if st.button("🗑️ Executar Limpeza dos Bancos Selecionados"):
                    if not (limpar_compras or limpar_saidas or limpar_pagamentos or limpar_doacoes or limpar_estoque):
                        st.warning("Selecione ao menos uma opção para executar a limpeza.")
                    elif not confirmar_limpeza:
                        st.error("Marque a caixa de seleção de confirmação acima para prosseguir.")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        mensagens_sucesso = []

                        if limpar_compras:
                            c.execute("DELETE FROM compras")
                            mensagens_sucesso.append("🛒 Histórico de compras zerado.")

                        if limpar_saidas:
                            c.execute("DELETE FROM saidas")
                            mensagens_sucesso.append("☕ Histórico de consumo/saídas zerado.")

                        if limpar_pagamentos:
                            c.execute("DELETE FROM pagamentos")
                            for arq in os.listdir(PASTA_COMPROVANTES):
                                arq_path = os.path.join(PASTA_COMPROVANTES, arq)
                                if os.path.isfile(arq_path):
                                    os.remove(arq_path)
                            mensagens_sucesso.append("💳 Histórico de pagamentos e comprovantes apagados.")

                        if limpar_doacoes:
                            c.execute("DELETE FROM doacoes")
                            c.execute("UPDATE usuarios SET pontos = 0")
                            mensagens_sucesso.append("🎁 Histórico de doações apagado e ranking zerado.")

                        if limpar_estoque:
                            c.execute("DELETE FROM estoque")
                            mensagens_sucesso.append("📦 Todos os itens do estoque foram removidos.")

                        conn.commit()
                        conn.close()

                        for msg in mensagens_sucesso:
                            st.success(msg)

                        st.rerun()

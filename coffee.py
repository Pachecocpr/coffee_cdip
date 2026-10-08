import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import json
import os
import base64
import urllib.parse
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão Café Coletivo - NextGen Office", 
    page_icon="☕", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURAÇÃO DE BANCO E IMAGEM DO GITHUB ---
DB_FILE = "cafe_coletivo.db"
ARQUIVO_CONFIG = "config_pix.json"
NOME_IMAGEM_LOCAL = "capa.jpg"
URL_RESERVA_CAPA = "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?q=80&w=1200&auto=format&fit=crop"

def obter_bg_css():
    """Converte a imagem local para Base64 para usar no CSS de fundo ou usa a URL reserva."""
    if os.path.exists(NOME_IMAGEM_LOCAL):
        with open(NOME_IMAGEM_LOCAL, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/jpeg;base64,{encoded_string}"
    return URL_RESERVA_CAPA

bg_url = obter_bg_css()

# --- APLICAÇÃO DE CSS FUTURISTA COM PLANO DE FUNDO (DARK NEON TECH) ---
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

    /* PLANO DE FUNDO COM OVERLAY ESCURO PARA FACILITAR LEITURA */
    .stApp {{
        background: linear-gradient(rgba(10, 14, 23, 0.85), rgba(22, 31, 51, 0.90)), url('{bg_url}') !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        font-family: 'Segoe UI', Roboto, sans-serif !important;
        color: #E2E8F0 !important;
    }}

    /* CARDS E FORMULÁRIOS COM EFEITO VIDRO (FROSTED GLASS) */
    div[data-testid="stForm"], div[data-testid="stExpander"], div.stContainer {{
        background: rgba(15, 23, 42, 0.85) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 240, 255, 0.15) !important;
        backdrop-filter: blur(12px) !important;
    }}

    h1, h2, h3 {{
        color: #00F0FF !important;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.4) !important;
        font-weight: 700 !important;
    }}

    div[data-testid="stFormSubmitButton"] > button, .stButton > button {{
        background: linear-gradient(90deg, #00F0FF 0%, #7000FF 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.4) !important;
    }}

    div[data-testid="stFormSubmitButton"] > button:hover, .stButton > button:hover {{
        transform: scale(1.02) !important;
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.7) !important;
    }}

    section[data-testid="stSidebar"] {{
        background-color: rgba(13, 17, 23, 0.92) !important;
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
        background: rgba(15, 23, 42, 0.85) !important;
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
                    quantidade REAL DEFAULT 0,
                    unidade TEXT NOT NULL
                )''')

    # Tabela de Compras/Entradas Financeiras
    c.execute('''CREATE TABLE IF NOT EXISTS compras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    comprador_id INTEGER,
                    item TEXT NOT NULL,
                    quantidade REAL NOT NULL,
                    valor_total REAL NOT NULL,
                    FOREIGN KEY(comprador_id) REFERENCES usuarios(id)
                )''')

    # Tabela de Doações (Sem custo)
    c.execute('''CREATE TABLE IF NOT EXISTS doacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    doador_id INTEGER,
                    item TEXT NOT NULL,
                    quantidade REAL NOT NULL,
                    pontos_ganhos INTEGER NOT NULL,
                    FOREIGN KEY(doador_id) REFERENCES usuarios(id)
                )''')

    # Criar usuário Master inicial caso não exista
    c.execute("SELECT * FROM usuarios WHERE perfil = 'Master'")
    if not c.fetchone():
        senha_admin = hashlib.sha256("Matrix@0580".encode()).hexdigest()
        c.execute("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
                  ("Célio Pacheco", "84130580", senha_admin, "Master"))
    
    conn.commit()
    conn.close()

    if not os.path.exists(ARQUIVO_CONFIG):
        config_inicial = {
            "chave_pix": "admin@empresa.com",
            "nome_recebedor": "GESTAO CAFE COLETIVO",
            "cidade_recebedor": "BELO HORIZONTE"
        }
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump(config_inicial, f)

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# --- FUNÇÕES DE UTILIDADE E CRIPTOGRAFIA ---
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_config():
    with open(ARQUIVO_CONFIG, "r") as f:
        return json.load(f)

def salvar_config(config):
    with open(ARQUIVO_CONFIG, "w") as f:
        json.dump(config, f)

# --- GERADOR PIX (EMV / QR CODE) ---
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
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()
    valor_str = f"{valor:.2f}" if valor > 0 else ""

    gui = "0014br.gov.bcb.pix"
    key = f"01{len(chave):02d}{chave}"
    merchant_account = f"26{len(gui + key):02d}{gui}{key}"

    cat = "52040000"
    currency = "5303986"
    amount = f"54{len(valor_str):02d}{valor_str}" if valor > 0 else ""
    country = "5802BR"
    merchant_name = f"59{len(nome):02d}{nome}"
    merchant_city = f"60{len(cidade):02d}{cidade}"

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
    payload_pix = gerar_payload_pix(config_pix["chave_pix"], config_pix["nome_recebedor"], config_pix["cidade_recebedor"])
    url_qr = obter_url_qr_code(payload_pix)

    with col1:
        st.image(url_qr, width=220)
    with col2:
        st.subheader("📲 Pagamento via Pix")
        st.write(f"**Chave Pix:** `{config_pix['chave_pix']}`")
        st.write(f"**Titular:** {config_pix['nome_recebedor']}")
        st.text_area("Copia e Cola Pix:", payload_pix, height=100)

    st.divider()
    st.subheader("📦 Itens Disponíveis no Momento")
    conn = get_db_connection()
    df_est = pd.read_sql_query("SELECT item as Item, categoria as Categoria, quantidade as Qtd, unidade as Unidade FROM estoque WHERE quantidade > 0", conn)
    conn.close()
    
    if not df_est.empty:
        st.dataframe(df_est, use_container_width=True)
    else:
        st.info("Estoque atual indisponível no momento.")

# ==========================================
# 🔐 SISTEMA PRINCIPAL (AUTENTICADO)
# ==========================================
else:
    if "usuario_logado" not in st.session_state:
        st.session_state["usuario_logado"] = None

    # --- TELA DE LOGIN & CADASTRO ---
    if not st.session_state["usuario_logado"]:
        st.title("☕ Gestão do Café Coletivo")
        
        tab_login, tab_cadastro = st.tabs(["🔒 Entrar", "📝 Aderir ao Café (Cadastrar)"])

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
                nome_cad = st.text_input("Nome Completo / Usuário de Login:")
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
                            st.success("Cadastro realizado com sucesso! Vá para a aba 'Entrar' para acessar.")
                        except sqlite3.IntegrityError:
                            st.error("E-mail já cadastrado no sistema.")
                    else:
                        st.warning("Preencha todos os campos do formulário.")

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

        opcoes_menu = ["📊 Dashboard & Métricas", "📦 Estoque Geral", "🛒 Informar Compra (Com Custo)", "🎁 Registrar Bônus/Doação", "🏆 Ranking de Doadores", "💳 Chave Pix & Contribuição"]
        
        if user["perfil"] in ["Master", "ADM"]:
            opcoes_menu.append("🛠️ Painel Master (Gestão)")

        opcao = st.sidebar.radio("Navegação", opcoes_menu)

        # ----------------------------------------------------
        # 1. DASHBOARD & MÉTRICAS
        # ----------------------------------------------------
        if opcao == "📊 Dashboard & Métricas":
            st.header("📊 Faturamento, Custos e Estoque")
            
            conn = get_db_connection()
            total_investido = pd.read_sql_query("SELECT SUM(valor_total) as total FROM compras", conn)["total"].fillna(0).iloc[0]
            total_itens_estoque = pd.read_sql_query("SELECT SUM(quantidade) as total FROM estoque", conn)["total"].fillna(0).iloc[0]
            total_doacoes = pd.read_sql_query("SELECT COUNT(*) as total FROM doacoes", conn)["total"].fillna(0).iloc[0]
            conn.close()

            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Investimento Total (Compras)", f"R$ {total_investido:.2f}")
            m2.metric("📦 Volume em Estoque (Un/Kg)", f"{total_itens_estoque:.1f}")
            m3.metric("🎁 Doações/Bônus Recebidos", f"{total_doacoes} registros")

            st.divider()

            conn = get_db_connection()
            df_compras = pd.read_sql_query("SELECT item, SUM(valor_total) as custo_total FROM compras GROUP BY item", conn)
            df_estoque = pd.read_sql_query("SELECT item, quantidade FROM estoque", conn)
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
                st.subheader("Nível do Estoque")
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
            df_estoque = pd.read_sql_query("SELECT item as Item, categoria as Categoria, quantidade as Qtd, unidade as Unidade FROM estoque", conn)
            conn.close()

            st.dataframe(df_estoque, use_container_width=True)

        # ----------------------------------------------------
        # 3. INFORMAR COMPRA (COM CUSTO)
        # ----------------------------------------------------
        elif opcao == "🛒 Informar Compra (Com Custo)":
            st.header("🛒 Registrar Compra para o Café")
            st.write("Comprou algo para a equipe e usou o fundo/dinheiro próprio? Cadastre aqui.")

            with st.form("form_compra"):
                item_nome = st.text_input("Item (ex: Café Solúvel, Açúcar, Leite):")
                categoria = st.selectbox("Categoria:", ["Insumos Básicos", "Matinais", "Descartáveis", "Snacks"])
                qtd = st.number_input("Quantidade Comprada:", min_value=0.1, step=0.5)
                unidade = st.selectbox("Unidade:", ["Unidades", "Kg", "Pacotes", "Caixas", "Litros"])
                valor_total = st.number_input("Valor Total Pago (R$):", min_value=0.01, step=1.0)
                
                btn_salvar_compra = st.form_submit_button("Registrar Compra e Atualizar Estoque")

                if btn_salvar_compra:
                    if item_nome:
                        conn = get_db_connection()
                        c = conn.cursor()
                        
                        # Inserir Compra
                        c.execute("INSERT INTO compras (data_hora, comprador_id, item, quantidade, valor_total) VALUES (?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], item_nome, qtd, valor_total))
                        
                        # Atualizar Estoque
                        c.execute("SELECT quantidade FROM estoque WHERE item = ?", (item_nome,))
                        res = c.fetchone()
                        if res:
                            c.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE item = ?", (qtd, item_nome))
                        else:
                            c.execute("INSERT INTO estoque (item, categoria, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                      (item_nome, categoria, qtd, unidade))
                        
                        conn.commit()
                        conn.close()
                        st.success("Compra registrada e estoque atualizado!")
                    else:
                        st.error("Informe o nome do item.")

        # ----------------------------------------------------
        # 4. REGISTRAR BÔNUS/DOAÇÃO (SEM CUSTO)
        # ----------------------------------------------------
        elif opcao == "🎁 Registrar Bônus/Doação":
            st.header("🎁 Doar Item Extra (Pontua no Ranking)")
            st.write("Trouxe algo de casa para compartilhar com o time sem pedir reembolso? Registre e receba pontos no ranking!")

            with st.form("form_doacao"):
                item_nome = st.text_input("Item Doador (ex: Bolo caseiro, Pó de café extra):")
                categoria = st.selectbox("Categoria:", ["Insumos Básicos", "Matinais", "Doces/Mimos", "Snacks"])
                qtd = st.number_input("Quantidade Doada:", min_value=1.0, step=1.0)
                unidade = st.selectbox("Unidade:", ["Unidades", "Kg", "Pacotes", "Litros"])
                
                btn_salvar_doacao = st.form_submit_button("Registrar Doação")

                if btn_salvar_doacao:
                    if item_nome:
                        pontos = int(qtd * 10)
                        conn = get_db_connection()
                        c = conn.cursor()
                        
                        # Inserir Doação
                        c.execute("INSERT INTO doacoes (data_hora, doador_id, item, quantidade, pontos_ganhos) VALUES (?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"], item_nome, qtd, pontos))
                        
                        # Atualizar Pontuação do Usuário
                        c.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pontos, user["id"]))

                        # Atualizar Estoque
                        c.execute("SELECT quantidade FROM estoque WHERE item = ?", (item_nome,))
                        res = c.fetchone()
                        if res:
                            c.execute("UPDATE estoque SET quantidade = quantidade + ? WHERE item = ?", (qtd, item_nome))
                        else:
                            c.execute("INSERT INTO estoque (item, categoria, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                      (item_nome, categoria, qtd, unidade))

                        conn.commit()
                        conn.close()
                        st.balloons()
                        st.success(f"Obrigado pela doação! Você ganhou +{pontos} pontos no Ranking!")
                    else:
                        st.error("Informe o item doado.")

        # ----------------------------------------------------
        # 5. RANKING DE DOADORES
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
        # 6. CHAVE PIX & CONTRIBUIÇÃO
        # ----------------------------------------------------
        elif opcao == "💳 Chave Pix & Contribuição":
            st.header("💳 Chave Pix Oficial do Café Coletivo")
            payload_pix = gerar_payload_pix(config_pix["chave_pix"], config_pix["nome_recebedor"], config_pix["cidade_recebedor"])
            url_qr = obter_url_qr_code(payload_pix)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(url_qr, width=220)
            with col2:
                st.write(f"**Chave Pix Registrada:** `{config_pix['chave_pix']}`")
                st.write(f"**Titular:** {config_pix['nome_recebedor']}")
                st.text_area("Copia e Cola Pix:", payload_pix, height=100)

            st.divider()

            url_atual = st.context.headers.get("host", "localhost:8501")
            link_convidado = f"https://{url_atual}/?modo=convidado"
            st.subheader("📲 Link de Acesso Rápido / Visitante")
            st.code(link_convidado)

        # ----------------------------------------------------
        # 7. PAINEL MASTER / ADM
        # ----------------------------------------------------
        elif opcao == "🛠️ Painel Master (Gestão)" and user["perfil"] in ["Master", "ADM"]:
            st.header("🛠️ Administração do Sistema e Perfis")

            tab_users, tab_pix_cfg = st.tabs(["👥 Controle de Usuários", "⚙️ Configurações Pix"])

            with tab_users:
                conn = get_db_connection()
                df_users = pd.read_sql_query("SELECT id, nome, email, perfil, ativo FROM usuarios", conn)
                conn.close()

                st.dataframe(df_users, use_container_width=True)

                st.subheader("Editar Perfil / Resetar Senha")
                col_u1, col_u2, col_u3 = st.columns(3)
                
                with col_u1:
                    user_selected_id = st.selectbox("Selecione o Usuário:", df_users["id"].tolist())
                with col_u2:
                    novo_perfil = st.selectbox("Novo Perfil:", ["Usuário", "ADM", "Convidado"])
                with col_u3:
                    nova_senha = st.text_input("Nova Senha (deixe em branco para não alterar):", type="password")

                if st.button("Salvar Alterações do Usuário"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (novo_perfil, user_selected_id))
                    
                    if nova_senha:
                        c.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (hash_senha(nova_senha), user_selected_id))
                    
                    conn.commit()
                    conn.close()
                    st.success("Dados do usuário atualizados com sucesso!")
                    st.rerun()

            with tab_pix_cfg:
                with st.form("form_config_pix_admin"):
                    chave = st.text_input("Chave Pix:", value=config_pix["chave_pix"])
                    nome = st.text_input("Nome do Recebedor:", value=config_pix["nome_recebedor"])
                    cidade = st.text_input("Cidade:", value=config_pix["cidade_recebedor"])
                    
                    if st.form_submit_button("Atualizar Configurações Pix"):
                        config_pix["chave_pix"] = chave
                        config_pix["nome_recebedor"] = nome
                        config_pix["cidade_recebedor"] = cidade
                        salvar_config(config_pix)
                        st.success("Configurações do Pix salvas!")
                        st.rerun()

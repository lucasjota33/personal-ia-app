import streamlit as st
import requests
import json
import hashlib
import secrets
import base64
from fpdf import FPDF 

# Configurações iniciais
CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash"

# ==========================================================
# 🟢 MOTOR DE BANCO DE DADOS EM NUVEM (FIREBASE FIRESTORE)
# ==========================================================
FIREBASE_PROJECT_ID = "treinadordigital-b8fe2"
FIREBASE_API_KEY = "AIzaSyBXmbHcwmGBZSMRCJyv-P7YtbslVydIbro"
# Rota secreta para a sua base de dados na nuvem
URL_FIRESTORE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/sistema/banco_de_dados?key={FIREBASE_API_KEY}"

def conversor_para_firestore(valor):
    """Traduz os dados do Python para a linguagem que o Google Firebase entende"""
    if isinstance(valor, dict):
        return {"mapValue": {"fields": {str(k): conversor_para_firestore(v) for k, v in valor.items()}}}
    elif isinstance(valor, list) or isinstance(valor, tuple):
        return {"arrayValue": {"values": [conversor_para_firestore(v) for v in valor]}}
    elif isinstance(valor, str):
        return {"stringValue": valor}
    elif isinstance(valor, bool):
        return {"booleanValue": valor}
    elif isinstance(valor, int):
        return {"integerValue": str(valor)}
    elif isinstance(valor, float):
        return {"doubleValue": valor}
    elif valor is None:
        return {"nullValue": None}
    else:
        return {"stringValue": str(valor)}

def conversor_para_python(valor):
    """Pega os dados do Firebase e traduz de volta para o Python"""
    if "mapValue" in valor:
        return {k: conversor_para_python(v) for k, v in valor["mapValue"].get("fields", {}).items()}
    elif "arrayValue" in valor:
        return [conversor_para_python(v) for v in valor["arrayValue"].get("values", [])]
    elif "stringValue" in valor:
        return valor["stringValue"]
    elif "integerValue" in valor:
        return int(valor["integerValue"])
    elif "doubleValue" in valor:
        return float(valor["doubleValue"])
    elif "booleanValue" in valor:
        return valor["booleanValue"]
    elif "nullValue" in valor:
        return None
    return None

def carregar_banco():
    """Puxa os dados da nuvem sempre que alguém abre o site"""
    try:
        resposta = requests.get(URL_FIRESTORE)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "fields" in dados:
                return {k: conversor_para_python(v) for k, v in dados["fields"].items()}
    except Exception:
        pass
    return {}

def salvar_banco(dados):
    """Salva os dados na nuvem em tempo real"""
    try:
        campos = {str(k): conversor_para_firestore(v) for k, v in dados.items()}
        payload = {"fields": campos}
        # Envia a atualização para a nuvem
        requests.patch(URL_FIRESTORE, json=payload)
    except Exception:
        pass

# --- FUNÇÕES DE SEGURANÇA ---
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def gerar_token_sessao():
    return secrets.token_hex(16)

# 🟢 FUNÇÃO DE LIMPEZA: Evita erros de caracteres especiais no PDF
def limpar_para_pdf(texto):
    if not texto: return ""
    substituicoes = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '-', '\u2026': '...',
        '\u00a0': ' ', '\u200b': ''
    }
    for char, sub in substituicoes.items():
        texto = texto.replace(char, sub)
    return texto.encode("latin-1", "ignore").decode("latin-1")

# 🟢 NOVA FUNÇÃO: LIMPEZA GERAL PARA TEXTOS DA IA
def limpar_none(texto):
    if texto is None:
        return ""
    texto = str(texto)
    for token in ["None", "none", "null", "Nil"]:
        texto = texto.replace(token, "")
    return texto.strip()

# 🟢 CLASSE DO PDF ELITE (Cabeçalhos com Logo, Rodapés e Design Premium)
class PDF_Elite(FPDF):
    def __init__(self, nome_atleta):
        super().__init__()
        self.nome_atleta = nome_atleta

    def header(self):
        # Tenta inserir a logo no canto superior esquerdo do PDF
        try:
            self.image("logo.png", 10, 8, 15)
            self.set_x(30) # Desloca o texto para a direita para não ficar em cima da imagem
        except:
            pass
            
        # Linha no topo de toda página
        self.set_font("Arial", "B", 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "PROTOCOLO DE ELITE", 0, 0, "L")
        self.cell(0, 10, f"Atleta: {self.nome_atleta}", 0, 1, "R")
        self.set_draw_color(30, 30, 30) # Linha cinza chumbo
        self.set_line_width(0.5)
        self.line(10, 20, 200, 20)
        self.ln(8)

    def footer(self):
        # Rodapé com numeração
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

# 🟢 MOTOR DE GERAR PDF (TABELAS INTELIGENTES NO FORMATO ORIGINAL)
@st.cache_data(show_spinner=False)
def gerar_pdf(texto_md, nome_atleta):
    pdf = PDF_Elite(nome_atleta)
    _ = pdf.add_page()
    _ = pdf.set_auto_page_break(True, margin=15) 
    
    # Capa Principal
    _ = pdf.set_font("Arial", "B", 20)
    _ = pdf.set_text_color(30, 30, 30) # Preto Premium 
    _ = pdf.ln(10)
    _ = pdf.multi_cell(0, 10, limpar_para_pdf(f"PLANEJAMENTO ESTRATÉGICO\n{nome_atleta.upper()}"), 0, "C")
    _ = pdf.ln(15)
    
    # + [""] garante que uma tabela no fim do documento seja renderizada
    linhas = texto_md.split("\n") + [""] 
    buffer_tabela = []
    em_tabela = False

    for linha in linhas:
        l_strip = linha.strip()

        # IDENTIFICA TABELAS E RENDERIZA A GRADE
        if l_strip.startswith('|'):
            em_tabela = True
            buffer_tabela.append(l_strip)
            continue
        elif em_tabela:
            if buffer_tabela:
                def extrair_celulas(linha_str):
                    s = linha_str.strip()
                    if s.startswith('|'): s = s[1:]
                    if s.endswith('|'): s = s[:-1]
                    return [c.strip() for c in s.split('|')]

                cols = extrair_celulas(buffer_tabela[0])
                if cols:
                    num_cols = len(cols)
                    if num_cols > 0:
                        w_col = 190 / num_cols
                        
                        def draw_row(dados_linha, eh_cabecalho=False, zebra=False):
                            if eh_cabecalho:
                                _ = pdf.set_font("Arial", "B", 9)
                            else:
                                _ = pdf.set_font("Arial", "", 8)
                                
                            max_l = 1
                            for txt in dados_linha:
                                txt_limpo = limpar_para_pdf(txt)
                                cw = pdf.get_string_width(txt_limpo)
                                w_seguro = w_col - 4 # Desconta padding lateral
                                if w_seguro <= 0: w_seguro = 1
                                linhas_txt = int(cw / w_seguro) + 1 
                                if linhas_txt > max_l: 
                                    max_l = linhas_txt
                                    
                            alt_linha = (5 * max_l) + 4 
                            
                            if pdf.get_y() + alt_linha > 275:
                                _ = pdf.add_page()
                                
                            y_ini = pdf.get_y()
                            
                            if eh_cabecalho:
                                _ = pdf.set_fill_color(30, 30, 30) # Fundo do cabeçalho em grafite
                                _ = pdf.set_text_color(255, 255, 255) # Letra Branca
                            else:
                                _ = pdf.set_text_color(40, 40, 40)
                                if zebra:
                                    _ = pdf.set_fill_color(245, 245, 245)
                                else:
                                    _ = pdf.set_fill_color(255, 255, 255)

                            for i, txt in enumerate(dados_linha):
                                x_ini = 10 + (i * w_col)
                                _ = pdf.set_xy(x_ini, y_ini)
                                _ = pdf.cell(w_col, alt_linha, "", 1, 0, "", True)
                                
                                _ = pdf.set_xy(x_ini, y_ini + 2) 
                                txt_limpo = limpar_para_pdf(txt)
                                _ = pdf.multi_cell(w_col, 5, txt_limpo, 0, "C")
                                
                            _ = pdf.set_xy(10, y_ini + alt_linha)

                        draw_row(cols, eh_cabecalho=True)
                        
                        zebra = False
                        for l_tab in buffer_tabela[1:]:
                            if '---' in l_tab: continue
                            dados = extrair_celulas(l_tab)
                            
                            if len(dados) < num_cols:
                                dados.extend([''] * (num_cols - len(dados)))
                            elif len(dados) > num_cols:
                                dados = dados[:num_cols]
                                
                            draw_row(dados, eh_cabecalho=False, zebra=zebra)
                            zebra = not zebra
                        
            _ = pdf.ln(5)
            buffer_tabela = []
            em_tabela = False

        if not l_strip: continue

        l_limpa = l_strip.replace("**", "").replace("* ", "- ")

        if l_strip.startswith('### '):
            _ = pdf.ln(2)
            _ = pdf.set_font("Arial", "B", 12)
            _ = pdf.set_text_color(40, 40, 40)
            _ = pdf.multi_cell(0, 7, limpar_para_pdf(l_limpa.replace('### ', '')))
        elif l_strip.startswith('## '):
            _ = pdf.ln(4)
            _ = pdf.set_font("Arial", "B", 14)
            _ = pdf.set_text_color(30, 30, 30) # Titulo 2 em grafite escuro
            _ = pdf.multi_cell(0, 8, limpar_para_pdf(l_limpa.replace('## ', '')))
        elif l_strip.startswith('# '):
            _ = pdf.ln(6)
            _ = pdf.set_font("Arial", "B", 18)
            _ = pdf.set_text_color(30, 30, 30) # Titulo 1 em grafite escuro
            _ = pdf.multi_cell(0, 10, limpar_para_pdf(l_limpa.replace('# ', '')))
            _ = pdf.set_draw_color(30, 30, 30)
            _ = pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            _ = pdf.ln(2)
        else:
            _ = pdf.set_font("Arial", "", 10)
            _ = pdf.set_text_color(60, 60, 60)
            
            if l_limpa.startswith('- '):
                _ = pdf.set_x(15)
                _ = pdf.multi_cell(0, 6, chr(149) + " " + limpar_para_pdf(l_limpa[2:]))
            else:
                _ = pdf.multi_cell(0, 6, limpar_para_pdf(l_limpa))
            _ = pdf.ln(1)

    resultado = pdf.output(dest="S")
    if isinstance(resultado, str):
        return resultado.encode("latin-1", "ignore")
    return bytes(resultado)

# Configuração da Página 
st.set_page_config(page_title="Treinador Digital Elite", page_icon="logo.png", layout="wide")

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    /* 1. Reset e Limpeza de Interface */
    [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton { display: none !important; visibility: hidden !important; }
    header { background-color: transparent !important; box-shadow: none !important; }
    #MainMenu, footer { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    .block-container { padding-top: 2rem !important; margin-top: 1rem !important; }

    /* 2. LAYOUT DE CHAT */
    .stMarkdown p, .stMarkdown li {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    
    /* 3. SCROLL NAS TABELAS (ESSENCIAL PARA CELULAR) */
    .stMarkdown table {
        display: block !important;
        vertical-align: middle !important;
        overflow-x: auto !important;
        white-space: nowrap !important; 
        max-width: 100% !important;
        -webkit-overflow-scrolling: touch; 
        border-radius: 8px; 
        margin-bottom: 20px;
    }

    /* 4. PADRONIZAÇÃO ELITE (MODO ESCURO) */
    @media (prefers-color-scheme: dark) {
        .stButton > button, div[data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
            background-color: #CCCCCC !important; 
            color: #000000 !important;
            border-radius: 10px !important;
            border: 1px solid #FFFFFF !important;
            transition: all 0.3s ease;
            font-weight: 700 !important;
            width: 100%;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            background-color: #FFFFFF !important;
            box-shadow: 0px 0px 15px rgba(255, 255, 255, 0.2) !important;
        }
        button[data-baseweb="tab"] { color: #888 !important; }
        button[aria-selected="true"] { color: #CCCCCC !important; }
        div[data-baseweb="tab-highlight"] { background-color: #CCCCCC !important; }
        div[data-baseweb="input"]:focus-within { border-color: #CCCCCC !important; box-shadow: 0 0 0 1px #CCCCCC !important; }
        input, textarea { caret-color: #CCCCCC !important; }
    }

    /* 5. PADRONIZAÇÃO ELITE (MODO CLARO) */
    @media (prefers-color-scheme: light) {
        .stButton > button, div[data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
            background-color: #1A1A1A !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            border: 1px solid #333333 !important;
            transition: all 0.3s ease;
            font-weight: 600 !important;
            width: 100%;
        }
        .stButton > button:hover, .stDownloadButton > button:hover { background-color: #333333 !important; }
        button[data-baseweb="tab"] { color: #888 !important; }
        button[aria-selected="true"] { color: #1A1A1A !important; }
        div[data-baseweb="tab-highlight"] { background-color: #1A1A1A !important; }
        div[data-baseweb="input"]:focus-within { border-color: #1A1A1A !important; box-shadow: 0 0 0 1px #1A1A1A !important; }
        input, textarea { caret-color: #1A1A1A !important; }
    }

    /* 6. Métrica e Notificação */
    div[data-testid="metric-container"] {
        background-color: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
    }
    div[data-testid="stNotification"] {
        background-color: rgba(128, 128, 128, 0.1) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }

    .stApp { overflow-x: hidden; }

    /* Ajustes específicos para celular */
    @media (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        .stButton > button { min-height: 50px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE ESTADO (MEMÓRIA DO APP) ---
if "etapa" not in st.session_state:
    st.session_state.etapa = 0 
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = {}
if "banco" not in st.session_state:
    st.session_state.banco = carregar_banco() 
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# 🟢 AUTO-LOGIN
if st.session_state.usuario_logado is None:
    token_url = st.query_params.get("session")
    if token_url:
        for user_key, user_data in st.session_state.banco.items():
            if user_data.get("token") == token_url:
                st.session_state.usuario_logado = user_key
                st.session_state.etapa = 1
                break

# ==========================================================
# ETAPA 0: TELA DE LOGIN, CADASTRO E LANDING PAGE
# ==========================================================
if st.session_state.etapa == 0:
    # --- HERO SECTION (Estilo Plataforma de Alta Conversão) ---
    st.markdown("""
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
            <span style="background-color: rgba(128,128,128,0.1); border: 1px solid rgba(128,128,128,0.2); padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 1px;">
                ⚡ O FUTURO DO TREINAMENTO ESPORTIVO
            </span>
            <h1 style="font-size: 3.5rem; font-weight: 800; margin-top: 1.5rem; line-height: 1.1; letter-spacing: -1px;">
                Transforme seu corpo com<br>
                <span style="background: -webkit-linear-gradient(45deg, #1A1A1A, #888888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">apenas um prompt</span>
            </h1>
            <p style="font-size: 1.2rem; color: #888; max-width: 600px; margin: 1.5rem auto; line-height: 1.6;">
                Treinos, dieta e suplementação milimetricamente calculados por IA. 
                Sem achismos. Sem treinos genéricos. Apenas resultados.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --- ÁREA DE LOGIN CENTRALIZADA ---
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        # 🟢 A Logo centralizada à prova de falhas (HTML Nativo) 🟢
        try:
            with open("logo.png", "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f'<div style="display: flex; justify-content: center; margin-bottom: 20px;">'
                f'<img src="data:image/png;base64,{img_b64}" width="140">'
                f'</div>', 
                unsafe_allow_html=True
            )
        except:
            pass
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta Nova"])
        
        with tab1:
            with st.form("form_login"):
                usuario_login = st.text_input("Usuário ou E-mail")
                senha_login = st.text_input("Senha", type="password")
                manter_conectado = st.checkbox("Mantenha-me conectado") 
                btn_login = st.form_submit_button("Acessar Plataforma", type="primary", use_container_width=True)
                
                if btn_login:
                    banco = st.session_state.banco
                    senha_hash = criptografar_senha(senha_login)
                    usuario_encontrado = None
                    
                    if usuario_login in banco and banco[usuario_login]["senha"] == senha_hash:
                        usuario_encontrado = usuario_login
                    else:
                        for user_key, user_data in banco.items():
                            if user_data.get("email") == usuario_login and user_data.get("senha") == senha_hash:
                                usuario_encontrado = user_key
                                break
                    
                    if usuario_encontrado:
                        st.session_state.usuario_logado = usuario_encontrado
                        st.session_state.etapa = 1
                        
                        if manter_conectado:
                            novo_token = gerar_token_sessao()
                            st.session_state.banco[usuario_encontrado]["token"] = novo_token
                            salvar_banco(st.session_state.banco)
                            st.query_params["session"] = novo_token
                            
                        st.rerun()
                    else:
                        st.error("Credenciais incorretas. Verifique seu usuário/e-mail e senha.")
                        
        with tab2:
            with st.form("form_cadastro"):
                novo_usuario = st.text_input("Escolha um Nome de Usuário")
                novo_email = st.text_input("Digite seu E-mail")
                nova_senha = st.text_input("Crie uma Senha", type="password")
                confirma_senha = st.text_input("Confirme a Senha", type="password")
                btn_cadastro = st.form_submit_button("Criar Conta", use_container_width=True)
                
                if btn_cadastro:
                    email_em_uso = any(dados.get("email") == novo_email for dados in st.session_state.banco.values())
                    
                    if not novo_usuario or not novo_email or not nova_senha or not confirma_senha:
                        st.error("Preencha todos os campos!")
                    elif nova_senha != confirma_senha:
                        st.error("As senhas não coincidem. Tente novamente.")
                    elif novo_usuario in st.session_state.banco:
                        st.error("Este nome de usuário já está em uso! Escolha outro.")
                    elif email_em_uso:
                        st.error("Este e-mail já está cadastrado no sistema!")
                    else:
                        st.session_state.banco[novo_usuario] = {
                            "email": novo_email,
                            "senha": criptografar_senha(nova_senha),
                            "token": "", 
                            "perfis": {}
                        }
                        salvar_banco(st.session_state.banco)
                        st.success("Conta criada com sucesso! Vá para a aba 'Entrar' para acessar.")

# ==========================================================
# ETAPA 1: PAINEL DO USUÁRIO (PERFIS + NOVO)
# ==========================================================
elif st.session_state.etapa == 1:
    
    usuario = st.session_state.usuario_logado
    perfis_do_usuario = st.session_state.banco[usuario]["perfis"]
    
    col_logout1, col_logout2 = st.columns([8, 2])
    with col_logout2:
        if st.button("Sair da Conta"):
            if "token" in st.session_state.banco[usuario]:
                st.session_state.banco[usuario]["token"] = ""
                salvar_banco(st.session_state.banco)
            st.query_params.clear()
            st.session_state.usuario_logado = None
            st.session_state.etapa = 0
            st.rerun()
            
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(f"Olá, {usuario}! 👋")
        
        if perfis_do_usuario:
            st.markdown("### 📋 Seus Atletas:")
            for nome_salvo in list(perfis_do_usuario.keys()):
                c_btn, c_del = st.columns([8, 2])
                with c_btn:
                    if st.button(f"👤 {nome_salvo}", key=f"btn_{nome_salvo}", use_container_width=True):
                        st.session_state.dados_usuario = perfis_do_usuario[nome_salvo]["dados"]
                        st.session_state.mensagens = perfis_do_usuario[nome_salvo]["mensagens"]
                        st.session_state.etapa = 2
                        st.rerun()
                with c_del:
                    if st.button("❌", key=f"del_{nome_salvo}"):
                        del st.session_state.banco[usuario]["perfis"][nome_salvo]
                        salvar_banco(st.session_state.banco)
                        st.rerun()
            
            st.divider()
            st.markdown("### ➕ Ou cadastre um Novo Atleta:")
        else:
            st.write("Você ainda não tem perfis salvos. Crie o primeiro abaixo!")
        
        with st.form("perfil_usuario"):
            nome = st.text_input("Nome Completo do Atleta", placeholder="Ex: Lucas")
            c_peso, c_altura = st.columns(2)
            with c_peso: peso = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
            with c_altura: altura = st.number_input("Altura (cm)", min_value=100, max_value=230, value=175, step=1)
                
            objetivo = st.selectbox("Objetivo Principal", ["Ganhar Massa Muscular (Hipertrofia)", "Perder Peso (Déficit Calórico)", "Melhorar Performance (Força/Resistência)", "Definição Corporal", "Manutenção da Saúde"])
            nivel_atividade = st.selectbox("Nível de Atividade Diária", ["Sedentário", "Levemente Ativo", "Moderadamente Ativo", "Muito Ativo", "Extremamente Ativo"])

            submit_button = st.form_submit_button(label="🚀 GERAR PROTOCOLO ELITE", type="primary", use_container_width=True)

        if submit_button:
            if not nome:
                st.error("⚠️ Identificação necessária.")
            elif nome in perfis_do_usuario:
                st.warning(f"⚠️ O atleta '{nome}' já existe! Exclua-o ou escolha outro nome.")
            else:
                st.session_state.dados_usuario = {"nome": nome, "peso": peso, "altura": altura, "objetivo": objetivo, "nivel": nivel_atividade}
                
                with st.spinner("⏳ Processando dados e estruturando planejamento..."):
                    prompt_mestre = f"""
                    Atue como um Nutricionista Esportivo Clínico e Personal Trainer de Atletas de Elite. 
                    Crie um planejamento irretocável para o(a) {nome}.
                    Peso: {peso}kg | Altura: {altura}cm | Nível: {nivel_atividade} | Objetivo: {objetivo}

                    # 🏆 PROTOCOLO DE ELITE: {nome.upper()}
                    ## 1. 📊 ANÁLISE METABÓLICA
                    Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
                    Taxa Metabólica Basal (Mifflin-St Jeor)| Gasto Energético Total | Meta Calórica Alvo

                    ## 2. 🍎 PLANO ALIMENTAR
                    | Refeição(Almoço, janta, etc) | Alimento Principal | Macronutrientes | Substituição |
                    
                    ## 3. 🏋️‍♂️ PLANILHA DE TREINAMENTO
                    Defina uma divisão semanal inteligente (ex:ABCDE, ABC, AB, Fullbody) com base no objetivo.
                    Para CADA DIA de treino, crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:

                    | Exercício | Séries | Repetições | Descanso |

                    ## 4. 💊 SUPLEMENTAÇÃO
                    | Suplemento | Dosagem Diária | Horário |
                    """

                    url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                    payload = {"contents": [{"parts": [{"text": prompt_mestre}]}]}
                    
                    try:
                        resposta = requests.post(url, json=payload, timeout=40)
                        if resposta.status_code == 200:
                            resposta_data = resposta.json()
                            texto_ia = resposta_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                            texto_ia = limpar_none(texto_ia)
                            st.session_state.mensagens = [{"role": "assistant", "content": texto_ia}]
                            
                            st.session_state.banco[usuario]["perfis"][nome] = {
                                "dados": st.session_state.dados_usuario,
                                "mensagens": st.session_state.mensagens
                            }
                            salvar_banco(st.session_state.banco)
                            
                            st.session_state.etapa = 2
                            st.rerun()
                        else:
                            st.error("Erro no Servidor. Tente novamente.")
                    except Exception as e:
                        st.error("Erro de conexão.")

# ==========================================================
# ETAPA 2: PÁGINA DO PLANO GERADO E CHAT DA IA
# ==========================================================
elif st.session_state.etapa == 2:
    
    usuario = st.session_state.usuario_logado
    dados = st.session_state.dados_usuario
    nome = dados["nome"]
    peso = dados["peso"]
    altura = dados["altura"]
    objetivo_curto = dados["objetivo"].split("(")[0].strip()
    imc = peso / ((altura / 100) ** 2)

    col_voltar, col_vazia = st.columns([4, 6])
    with col_voltar:
        if st.button("⬅️ Voltar ao Painel"):
            st.session_state.etapa = 1
            st.session_state.mensagens = []
            st.rerun()

    st.success(f"**Análise concluída, {nome}!** Confira seu protocolo abaixo.")
    
    c1, c2 = st.columns(2)
    c1.metric("Atleta", nome)
    c2.metric("Objetivo", objetivo_curto)
    
    c3, c4 = st.columns(2)
    c3.metric("Peso Atual", f"{peso} kg")
    c4.metric("IMC Inicial", f"{imc:.1f}")
    
    st.divider()
    
    for msg in st.session_state.mensagens:
        conteudo = limpar_none(msg.get("content"))
        role = msg.get("role")
        
        if role == "user":
            st.markdown(f"""
                <div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'>
                    <div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%; font-family: sans-serif; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>
                        {conteudo}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
            st.markdown(conteudo)
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    plano_principal = limpar_none(st.session_state.mensagens[0].get("content")) if st.session_state.mensagens else ""
    
    pdf_final = gerar_pdf(plano_principal, nome)
    
    st.download_button(
        label="📥 Baixar Protocolo Completo em PDF",
        data=pdf_final,
        file_name=f"Protocolo_{nome.replace(' ', '_')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )
            
    st.divider()
    st.subheader("💬 Central de Dúvidas")
    if prompt_duvida := st.chat_input("Pergunte sobre exercícios ou substituições de alimentos..."):
        
        st.session_state.mensagens.append({"role": "user", "content": prompt_duvida})
        
        st.markdown(f"""
            <div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'>
                <div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%; font-family: sans-serif; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>
                    {prompt_duvida}
                </div>
            </div>
        """, unsafe_allow_html=True)
            
        with st.spinner("Analisando protocolo..."):
            plano_contexto = st.session_state.mensagens[0]["content"]
            prompt_duvida_completo = f"Plano:\n{plano_contexto}\n\nDúvida: {prompt_duvida}"
            
            url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
            payload = {"contents": [{"parts": [{"text": prompt_duvida_completo}]}]}
            
            try:
                resposta = requests.post(url, json=payload, timeout=20)
                if resposta.status_code == 200:
                    resposta_data = resposta.json()
                    texto_ia_duvida = resposta_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    texto_ia_duvida = limpar_none(texto_ia_duvida)
                    
                    st.markdown(f"<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
                    st.markdown(texto_ia_duvida)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.session_state.mensagens.append({"role": "assistant", "content": texto_ia_duvida})
                    
                    st.session_state.banco[usuario]["perfis"][nome]["mensagens"] = st.session_state.mensagens
                    salvar_banco(st.session_state.banco)
                else:
                    st.warning("Servidor ocupado. Tente perguntar em alguns instantes.")
            except:
                st.error("Erro ao conectar.")
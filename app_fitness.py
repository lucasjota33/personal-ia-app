import streamlit as st
import requests
import json
import os
import hashlib
import secrets
import datetime
from fpdf import FPDF 

# Configurações iniciais da Página (DEVE SER A PRIMEIRA LINHA DO STREAMLIT)
st.set_page_config(page_title="Treinador IA Elite", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash"
ARQUIVO_BANCO = "banco_dados_saas.json"

# --- FUNÇÕES DO BANCO DE DADOS E SEGURANÇA ---
def carregar_banco():
    if os.path.exists(ARQUIVO_BANCO):
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_banco(dados):
    with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def gerar_token_sessao():
    return secrets.token_hex(16)

# --- FUNÇÕES DO PDF (MANTIDAS EXATAMENTE COMO VOCÊ GOSTOU) ---
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

def limpar_none(texto):
    if texto is None: return ""
    texto = str(texto)
    for token in ["None", "none", "null", "Nil"]:
        texto = texto.replace(token, "")
    return texto.strip()

class PDF_Elite(FPDF):
    def __init__(self, nome_atleta):
        super().__init__()
        self.nome_atleta = nome_atleta

    def header(self):
        self.set_font("Arial", "B", 9)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, "PROTOCOLO DE ELITE", 0, 0, "L")
        self.cell(0, 10, f"Atleta: {self.nome_atleta}", 0, 1, "R")
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.3)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

@st.cache_data(show_spinner=False)
def gerar_pdf(texto_md, nome_atleta, objetivo_atleta):
    pdf = PDF_Elite(nome_atleta)
    _ = pdf.add_page()
    _ = pdf.set_auto_page_break(True, margin=15) 
    
    _ = pdf.set_draw_color(220, 220, 220)
    _ = pdf.set_fill_color(255, 220, 0) 
    _ = pdf.rect(10, 25, 12, 255, 'F')
    
    _ = pdf.set_xy(28, 30)
    _ = pdf.set_font("Arial", "B", 10)
    _ = pdf.set_text_color(40, 40, 40)
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    _ = pdf.cell(80, 8, f"DATA: {hoje}", 1, 1, "C")
    
    _ = pdf.set_xy(30, 50)
    _ = pdf.set_font("Arial", "B", 24)
    _ = pdf.set_text_color(255, 220, 0) 
    _ = pdf.multi_cell(0, 12, "PLANEJADOR DE PROTOCOLO", 0, "C")
    
    _ = pdf.set_draw_color(220, 220, 220)
    
    pdf.ln(10)
    def draw_planner_block(label, data):
        _ = pdf.set_x(30)
        _ = pdf.set_font("Arial", "B", 9)
        _ = pdf.set_text_color(28, 131, 225) 
        _ = pdf.cell(0, 5, label.upper(), 0, 1, "L")
        _ = pdf.set_x(30)
        _ = pdf.set_font("Arial", "", 11)
        _ = pdf.set_text_color(60, 60, 60)
        _ = pdf.multi_cell(0, 7, data, 1, "C")
        pdf.ln(3)

    draw_planner_block("ATLETA", nome_atleta.upper())
    draw_planner_block("OBJETIVO PRINCIPAL", objetivo_atleta)
    _ = pdf.add_page()
    
    linhas = texto_md.split("\n") + [""] 
    buffer_tabela = []
    em_tabela = False

    for linha in linhas:
        l_strip = linha.strip()

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
                            _ = pdf.set_font("Arial", "", 8)
                            max_l = 1
                            for txt in dados_linha:
                                txt_limpo = limpar_para_pdf(txt)
                                cw = pdf.get_string_width(txt_limpo)
                                w_seguro = w_col - 5 
                                if w_seguro <= 0: w_seguro = 1
                                linhas_txt = int(cw / w_seguro) + 1 
                                if linhas_txt > max_l: max_l = linhas_txt
                                    
                            alt_linha = (5 * max_l) + 4
                            if pdf.get_y() + alt_linha > 275: _ = pdf.add_page()
                            y_ini = pdf.get_y()
                            
                            _ = pdf.set_draw_color(220, 220, 220) 

                            if eh_cabecalho:
                                pdf.set_font("Arial", "B", 9)
                                _ = pdf.set_fill_color(240, 240, 240) 
                                _ = pdf.set_text_color(40, 40, 40)
                            else:
                                _ = pdf.set_text_color(60, 60, 60)
                                if zebra:
                                    _ = pdf.set_fill_color(250, 250, 250)
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
                            if len(dados) < num_cols: dados.extend([''] * (num_cols - len(dados)))
                            elif len(dados) > num_cols: dados = dados[:num_cols]
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
            _ = pdf.set_text_color(255, 220, 0) 
            _ = pdf.multi_cell(0, 8, limpar_para_pdf(l_limpa.replace('## ', '')))
        elif l_strip.startswith('# '):
            _ = pdf.ln(6)
            _ = pdf.set_font("Arial", "B", 18)
            _ = pdf.set_text_color(255, 220, 0)
            _ = pdf.multi_cell(0, 10, limpar_para_pdf(l_limpa.replace('# ', '')))
            _ = pdf.set_draw_color(255, 220, 0)
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
    if isinstance(resultado, str): return resultado.encode("latin-1", "ignore")
    return bytes(resultado)

# --- CSS CUSTOMIZADO (MODO TECH FITNESS) ---
# Forçamos um design escuro com detalhes em neon (Laranja/Amarelo)
st.markdown("""
    <style>
    /* Ocultar elementos padrão do Streamlit */
    [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton { display: none !important; visibility: hidden !important; }
    header { background-color: transparent !important; box-shadow: none !important; }
    #MainMenu, footer { display: none !important; }
    
    /* Fundo App */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Estilização dos Botões Principais */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #FF8C00 0%, #FFD700 100%);
        color: #121212 !important;
        border: none;
        border-radius: 8px;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
        transition: all 0.3s ease-in-out;
        box-shadow: 0px 4px 15px rgba(255, 140, 0, 0.3);
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0px 6px 20px rgba(255, 215, 0, 0.6);
    }
    
    /* Estilização dos Cards de Métrica (HUD Style) */
    div[data-testid="metric-container"] {
        background-color: #1A1C23;
        border: 1px solid #2D303E;
        border-left: 4px solid #FF8C00;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        border-left: 4px solid #FFD700;
    }
    div[data-testid="metric-container"] label {
        color: #A0AEC0 !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div {
        color: #FFFFFF !important;
        font-size: 1.8rem !important;
        font-weight: bold;
    }
    
    /* Inputs e Selects Modernos */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stNumberInput>div>div>input {
        background-color: #1A1C23 !important;
        color: white !important;
        border: 1px solid #2D303E !important;
        border-radius: 6px !important;
    }
    .stTextInput>div>div>input:focus, .stSelectbox>div>div>select:focus {
        border-color: #FF8C00 !important;
        box-shadow: 0 0 5px rgba(255, 140, 0, 0.5) !important;
    }
    
    /* Painel do Chat */
    .stChatMessage {
        background-color: #1A1C23 !important;
        border-radius: 8px;
        border: 1px solid #2D303E;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE ESTADO (MEMÓRIA DO APP) ---
if "etapa" not in st.session_state: st.session_state.etapa = 0 
if "mensagens" not in st.session_state: st.session_state.mensagens = []
if "dados_usuario" not in st.session_state: st.session_state.dados_usuario = {}
if "banco" not in st.session_state: st.session_state.banco = carregar_banco() 
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None

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
# ETAPA 0: TELA DE LOGIN E CADASTRO
# ==========================================================
if st.session_state.etapa == 0:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: #FF8C00;'>⚡ TREINADOR IA ELITE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #A0AEC0;'>Performance extrema guiada por Inteligência Artificial.</p>", unsafe_allow_html=True)
        st.write("")
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta Nova"])
        
        with tab1:
            with st.form("form_login"):
                usuario_login = st.text_input("Usuário ou E-mail")
                senha_login = st.text_input("Senha", type="password")
                manter_conectado = st.checkbox("Mantenha-me conectado") 
                btn_login = st.form_submit_button("ACESSAR PORTAL", use_container_width=True)
                
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
                        st.error("Credenciais incorretas.")
                        
        with tab2:
            with st.form("form_cadastro"):
                novo_usuario = st.text_input("Escolha um Nome de Usuário")
                novo_email = st.text_input("Digite seu E-mail")
                nova_senha = st.text_input("Crie uma Senha", type="password")
                confirma_senha = st.text_input("Confirme a Senha", type="password")
                btn_cadastro = st.form_submit_button("CRIAR CONTA", use_container_width=True)
                
                if btn_cadastro:
                    email_em_uso = any(dados.get("email") == novo_email for dados in st.session_state.banco.values())
                    if not novo_usuario or not novo_email or not nova_senha or not confirma_senha: st.error("Preencha todos os campos!")
                    elif nova_senha != confirma_senha: st.error("As senhas não coincidem.")
                    elif novo_usuario in st.session_state.banco: st.error("Usuário já existe.")
                    elif email_em_uso: st.error("E-mail já cadastrado!")
                    else:
                        st.session_state.banco[novo_usuario] = {"email": novo_email, "senha": criptografar_senha(nova_senha), "token": "", "perfis": {}}
                        salvar_banco(st.session_state.banco)
                        st.success("Conta criada! Vá em 'Entrar'.")

# ==========================================================
# MENU LATERAL (SIDEBAR) - ATIVO NAS ETAPAS 1 E 2
# ==========================================================
if st.session_state.etapa in [1, 2]:
    usuario = st.session_state.usuario_logado
    perfis_do_usuario = st.session_state.banco[usuario]["perfis"]
    
    with st.sidebar:
        st.markdown(f"<h3 style='color: #FF8C00;'>Painel do Usuário</h3>", unsafe_allow_html=True)
        st.write(f"Bem-vindo(a), **{usuario}**")
        st.divider()
        
        st.markdown("#### 📋 Seus Atletas")
        if perfis_do_usuario:
            for nome_salvo in list(perfis_do_usuario.keys()):
                colA, colB = st.columns([8, 2])
                with colA:
                    if st.button(f"👤 {nome_salvo}", key=f"btn_{nome_salvo}", use_container_width=True):
                        st.session_state.dados_usuario = perfis_do_usuario[nome_salvo]["dados"]
                        st.session_state.mensagens = perfis_do_usuario[nome_salvo]["mensagens"]
                        st.session_state.etapa = 2
                        st.rerun()
                with colB:
                    if st.button("❌", key=f"del_{nome_salvo}"):
                        del st.session_state.banco[usuario]["perfis"][nome_salvo]
                        salvar_banco(st.session_state.banco)
                        st.rerun()
        else:
            st.info("Nenhum atleta cadastrado.")
            
        st.divider()
        if st.button("➕ NOVO ATLETA", use_container_width=True):
            st.session_state.etapa = 1
            st.rerun()
            
        st.write("")
        if st.button("Sair da Conta 🚪", use_container_width=True):
            if "token" in st.session_state.banco[usuario]:
                st.session_state.banco[usuario]["token"] = ""
                salvar_banco(st.session_state.banco)
            st.query_params.clear()
            st.session_state.usuario_logado = None
            st.session_state.etapa = 0
            st.rerun()

# ==========================================================
# ETAPA 1: CADASTRO DE NOVO ATLETA
# ==========================================================
if st.session_state.etapa == 1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='color: white;'>Criar Novo Planejamento</h2>", unsafe_allow_html=True)
        st.markdown("Preencha os dados fisiológicos do atleta para o cálculo da IA.")
        
        with st.form("perfil_usuario"):
            nome = st.text_input("Nome Completo do Atleta", placeholder="Ex: Lucas")
            c_peso, c_altura = st.columns(2)
            with c_peso: peso = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
            with c_altura: altura = st.number_input("Altura (cm)", min_value=100, max_value=230, value=175, step=1)
                
            objetivo = st.selectbox("Objetivo Principal", ["Ganhar Massa Muscular (Hipertrofia)", "Perder Peso (Déficit Calórico)", "Melhorar Performance (Força/Resistência)", "Definição Corporal", "Manutenção da Saúde"])
            nivel_atividade = st.selectbox("Nível de Atividade Diária", ["Sedentário", "Levemente Ativo", "Moderadamente Ativo", "Muito Ativo", "Extremamente Ativo"])

            submit_button = st.form_submit_button(label="🚀 GERAR PROTOCOLO ELITE", use_container_width=True)

        if submit_button:
            if not nome: st.error("⚠️ Identificação necessária.")
            elif nome in perfis_do_usuario: st.warning(f"⚠️ O atleta '{nome}' já existe! Exclua-o no menu lateral ou escolha outro nome.")
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
                        else: st.error("Erro no Servidor. Tente novamente.")
                    except: st.error("Erro de conexão.")

# ==========================================================
# ETAPA 2: DASHBOARD DO PLANO GERADO E CHAT DA IA
# ==========================================================
elif st.session_state.etapa == 2:
    dados = st.session_state.dados_usuario
    nome = dados["nome"]
    peso = dados["peso"]
    altura = dados["altura"]
    objetivo_atleta = dados["objetivo"] 
    objetivo_curto = dados["objetivo"].split("(")[0].strip()
    imc = peso / ((altura / 100) ** 2)

    st.markdown(f"<h2 style='color: white;'>Análise de <span style='color: #FF8C00;'>{nome}</span> Concluída! 🚀</h2>", unsafe_allow_html=True)
    
    # 🟢 CARDS ESTILO DASHBOARD PREMIUM
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status Atual", "Protocolo Ativo")
    c2.metric("Objetivo", objetivo_curto)
    c3.metric("Peso Base", f"{peso} kg")
    c4.metric("IMC Calculado", f"{imc:.1f}")
    
    st.divider()
    
    # Download do PDF posicionado acima do chat para fácil acesso
    plano_principal = limpar_none(st.session_state.mensagens[0].get("content")) if st.session_state.mensagens else ""
    pdf_final = gerar_pdf(plano_principal, nome, objetivo_atleta)
    
    col_pdf, col_vazia = st.columns([1, 2])
    with col_pdf:
        st.download_button(
            label="📥 EXPORTAR PROTOCOLO (PDF)",
            data=pdf_final,
            file_name=f"Protocolo_{nome.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    
    st.divider()
    
    for msg in st.session_state.mensagens:
        conteudo = limpar_none(msg.get("content"))
        if msg.get("role") == "assistant":
            st.markdown(conteudo)
        else:
            with st.chat_message("user"):
                st.markdown(conteudo)
    
    st.divider()
    st.subheader("💬 Central de Ajustes IA")
    if prompt_duvida := st.chat_input("Ex: 'Substitua a aveia por pão' ou 'Me dê um treino mais curto'"):
        st.session_state.mensagens.append({"role": "user", "content": prompt_duvida})
        with st.chat_message("user"):
            st.markdown(prompt_duvida)
            
        with st.chat_message("assistant"):
            with st.spinner("Recalculando variáveis..."):
                plano_contexto = st.session_state.mensagens[0]["content"]
                prompt_duvida_completo = f"Plano atual:\n{plano_contexto}\n\nDúvida/Ajuste do usuário: {prompt_duvida}"
                
                url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                payload = {"contents": [{"parts": [{"text": prompt_duvida_completo}]}]}
                
                try:
                    resposta = requests.post(url, json=payload, timeout=20)
                    if resposta.status_code == 200:
                        resposta_data = resposta.json()
                        texto_ia_duvida = resposta_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                        texto_ia_duvida = limpar_none(texto_ia_duvida)
                        st.markdown(texto_ia_duvida)
                        st.session_state.mensagens.append({"role": "assistant", "content": texto_ia_duvida})
                        
                        st.session_state.banco[st.session_state.usuario_logado]["perfis"][nome]["mensagens"] = st.session_state.mensagens
                        salvar_banco(st.session_state.banco)
                    else: st.warning("Servidor ocupado.")
                except: st.error("Erro ao conectar.")
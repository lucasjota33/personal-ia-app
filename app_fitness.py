import streamlit as st
import streamlit.components.v1 as components

# 🟢 OBRIGATÓRIO: Este comando DEVE ser o primeiro do Streamlit na página!
st.set_page_config(page_title="Treinador Digital Elite", page_icon="logo.png", layout="wide")

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
URL_FIRESTORE = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/sistema/banco_de_dados?key={FIREBASE_API_KEY}"

def conversor_para_firestore(valor):
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
    if not valor: return None
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
    try:
        resposta = requests.get(URL_FIRESTORE, timeout=15)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "fields" in dados:
                return {k: conversor_para_python(v) for k, v in dados["fields"].items()}
    except Exception:
        pass
    return {}

def salvar_banco(dados):
    try:
        campos = {str(k): conversor_para_firestore(v) for k, v in dados.items()}
        payload = {"fields": campos}
        requests.patch(URL_FIRESTORE, json=payload, timeout=15)
    except Exception:
        pass

# --- FUNÇÕES DE SEGURANÇA E UTILIDADE ---
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def gerar_token_sessao():
    return secrets.token_hex(16)

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

def exibir_mensagem(texto, tipo="info"):
    icone = "info"
    if tipo == "error": icone = "error"
    elif tipo == "success": icone = "check_circle"
    elif tipo == "warning": icone = "warning"
    
    st.markdown(f"""
        <div style="background-color: rgba(128,128,128,0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.2); color: #888; display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <span class="material-symbols-outlined">{icone}</span> 
            <span>{texto}</span>
        </div>
    """, unsafe_allow_html=True)

# 🟢 CLASSE DO PDF ELITE
class PDF_Elite(FPDF):
    def __init__(self, nome_atleta):
        super().__init__()
        self.nome_atleta = nome_atleta

    def header(self):
        try:
            self.image("logo.png", 10, 8, 15)
            self.set_x(30)
        except:
            pass
        self.set_font("Arial", "B", 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "PROTOCOLO DE ELITE", 0, 0, "L")
        self.cell(0, 10, f"Atleta: {self.nome_atleta}", 0, 1, "R")
        self.set_draw_color(30, 30, 30)
        self.set_line_width(0.5)
        self.line(10, 20, 200, 20)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

@st.cache_data(show_spinner=False)
def gerar_pdf(texto_md, nome_atleta):
    pdf = PDF_Elite(nome_atleta)
    _ = pdf.add_page()
    _ = pdf.set_auto_page_break(True, margin=15) 
    
    _ = pdf.set_font("Arial", "B", 20)
    _ = pdf.set_text_color(30, 30, 30)
    _ = pdf.ln(10)
    _ = pdf.multi_cell(0, 10, limpar_para_pdf(f"PLANEJAMENTO ESTRATÉGICO\n{nome_atleta.upper()}"), 0, "C")
    _ = pdf.ln(15)
    
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
                            if eh_cabecalho:
                                _ = pdf.set_font("Arial", "B", 9)
                            else:
                                _ = pdf.set_font("Arial", "", 8)
                                
                            max_l = 1
                            for txt in dados_linha:
                                txt_limpo = limpar_para_pdf(txt)
                                cw = pdf.get_string_width(txt_limpo)
                                w_seguro = w_col - 4
                                if w_seguro <= 0: w_seguro = 1
                                linhas_txt = int(cw / w_seguro) + 1 
                                if linhas_txt > max_l: 
                                    max_l = linhas_txt
                                    
                            alt_linha = (5 * max_l) + 4 
                            
                            if pdf.get_y() + alt_linha > 275:
                                _ = pdf.add_page()
                                
                            y_ini = pdf.get_y()
                            
                            if eh_cabecalho:
                                _ = pdf.set_fill_color(30, 30, 30)
                                _ = pdf.set_text_color(255, 255, 255)
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
            _ = pdf.set_text_color(30, 30, 30)
            _ = pdf.multi_cell(0, 8, limpar_para_pdf(l_limpa.replace('## ', '')))
        elif l_strip.startswith('# '):
            _ = pdf.ln(6)
            _ = pdf.set_font("Arial", "B", 18)
            _ = pdf.set_text_color(30, 30, 30)
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


# 🟢 CSS CUSTOMIZADO
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');
[data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton { display: none !important; visibility: hidden !important; }
header { background-color: transparent !important; box-shadow: none !important; }
#MainMenu, footer { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.block-container { padding-top: 2rem !important; margin-top: 1rem !important; }
div[data-testid="stNotification"] { display: none !important; }
.stMarkdown table {
    display: block !important; overflow-x: auto !important; white-space: nowrap !important; 
    max-width: 100% !important; width: 100% !important; border-radius: 8px; margin-bottom: 20px;
    -webkit-overflow-scrolling: touch;
}
div[data-testid="stMarkdownContainer"] { overflow-x: auto !important; }
.stButton > button, div[data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
    border-radius: 8px !important; transition: all 0.3s ease; min-height: 45px;
}
.stApp { overflow-x: hidden; }
@media (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    .stButton > button { min-height: 50px !important; }
}
::selection { background: rgba(128,128,128,0.3) !important; color: inherit !important; }
button[data-baseweb="tab"] p, button[data-baseweb="tab"] span { color: #888888 !important; transition: color 0.2s ease; }
div[data-baseweb="tab-highlight"] { background-color: #555555 !important; }
@media (prefers-color-scheme: dark) {
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within { border-color: #CCCCCC !important; box-shadow: 0 0 0 1px #CCCCCC !important; }
    button[data-baseweb="tab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] span { color: #FFFFFF !important; font-weight: 600 !important; }
}
@media (prefers-color-scheme: light) {
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within { border-color: #1A1A1A !important; box-shadow: 0 0 0 1px #1A1A1A !important; }
    button[data-baseweb="tab"]:hover p, button[data-baseweb="tab"]:hover span,
    button[data-baseweb="tab"]:focus p, button[data-baseweb="tab"]:focus span,
    button[data-baseweb="tab"]:active p, button[data-baseweb="tab"]:active span,
    button[data-baseweb="tab"][aria-selected="true"] p, button[data-baseweb="tab"][aria-selected="true"] span { color: #1A1A1A !important; font-weight: 600 !important; }
}
</style>
""", unsafe_allow_html=True)


# --- GERENCIADOR DE ESTADO ---
if "etapa" not in st.session_state: st.session_state.etapa = 0 
if "mensagens" not in st.session_state: st.session_state.mensagens = []
if "dados_usuario" not in st.session_state: st.session_state.dados_usuario = {}
if "banco" not in st.session_state: st.session_state.banco = carregar_banco() 
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "scroll_top" not in st.session_state: st.session_state.scroll_top = False

# 🟢 MOTOR DE SCROLL
if st.session_state.scroll_top:
    components.html("<script>var body = window.parent.document.querySelector('.main'); if (body) { body.scrollTo(0, 0); } window.parent.scrollTo(0, 0);</script>", height=0)
    st.session_state.scroll_top = False

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
# ETAPA 0: LOGIN / CADASTRO
# ==========================================================
if st.session_state.etapa == 0:
    st.markdown("""
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
            <span style="display: inline-flex; align-items: center; gap: 6px; background-color: rgba(128,128,128,0.1); border: 1px solid rgba(128,128,128,0.2); padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 1px;">
                <span class="material-symbols-outlined" style="font-size: 16px;">bolt</span> O FUTURO DO TREINAMENTO ESPORTIVO
            </span>
            <h1 style="font-size: 3.5rem; font-weight: 800; margin-top: 1.5rem; line-height: 1.1; letter-spacing: -1px;">Transforme seu corpo com<br><span style="background: -webkit-linear-gradient(45deg, #1A1A1A, #888888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">apenas um prompt</span></h1>
            <p style="font-size: 1.2rem; color: #888; max-width: 600px; margin: 1.5rem auto; line-height: 1.6;">Treinos, dieta e suplementação milimetricamente calculados por IA. Apenas resultados.</p>
        </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try:
            with open("logo.png", "rb") as f: img_b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<div style="display: flex; justify-content: center; margin-bottom: 20px;"><img src="data:image/png;base64,{img_b64}" width="140"></div>', unsafe_allow_html=True)
        except: pass
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta Nova"])
        with tab1:
            with st.form("form_login"):
                u_login = st.text_input("Usuário ou E-mail")
                s_login = st.text_input("Senha", type="password")
                manter = st.checkbox("Mantenha-me conectado") 
                if st.form_submit_button("Acessar Plataforma", type="primary", use_container_width=True):
                    senha_hash = criptografar_senha(s_login)
                    u_encontrado = None
                    if u_login in st.session_state.banco and st.session_state.banco[u_login].get("senha") == senha_hash: u_encontrado = u_login
                    else:
                        for k, v in st.session_state.banco.items():
                            if v.get("email") == u_login and v.get("senha") == senha_hash:
                                u_encontrado = k
                                break
                    if u_encontrado:
                        st.session_state.usuario_logado = u_encontrado
                        st.session_state.etapa = 1
                        st.session_state.scroll_top = True
                        if manter:
                            token = gerar_token_sessao()
                            st.session_state.banco[u_encontrado]["token"] = token
                            salvar_banco(st.session_state.banco)
                            st.query_params["session"] = token
                        st.rerun()
                    else: exibir_mensagem("Credenciais incorretas.", "error")
        with tab2:
            with st.form("form_cadastro"):
                novo_u = st.text_input("Usuário")
                novo_e = st.text_input("E-mail")
                nova_s = st.text_input("Senha", type="password")
                conf_s = st.text_input("Confirme a Senha", type="password")
                if st.form_submit_button("Criar Conta", type="primary", use_container_width=True):
                    if not novo_u or not novo_e or not nova_s: exibir_mensagem("Preencha tudo!", "warning")
                    elif nova_s != conf_s: exibir_mensagem("Senhas não coincidem.", "warning")
                    elif novo_u in st.session_state.banco: exibir_mensagem("Usuário já existe.", "warning")
                    else:
                        st.session_state.banco[novo_u] = {"email": novo_e, "senha": criptografar_senha(nova_s), "token": "", "perfis": {}}
                        salvar_banco(st.session_state.banco)
                        exibir_mensagem("Conta criada! Acesse na aba Entrar.", "success")

# ==========================================================
# ETAPA 1: PAINEL (VERIFICAÇÃO DE CHAVES)
# ==========================================================
elif st.session_state.etapa == 1:
    usuario = st.session_state.usuario_logado
    
    # 🟢 VACINA DEFINITIVA: Se o usuário logado por algum motivo for None no banco, ou não tiver a chave perfis
    if not st.session_state.banco.get(usuario): 
        st.session_state.banco = carregar_banco()
        
    if "perfis" not in st.session_state.banco.get(usuario, {}):
        if usuario in st.session_state.banco:
            st.session_state.banco[usuario]["perfis"] = {}
            salvar_banco(st.session_state.banco)
        else:
            st.session_state.etapa = 0
            st.rerun()

    perfis = st.session_state.banco[usuario]["perfis"]
    
    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown(f"<div style='text-align: center; margin-bottom: 2rem;'><p style='color: #888; font-size: 0.9rem; font-weight: 600;'>PAINEL DE CONTROLE</p><h1 style='font-size: 2.2rem; margin-top: 0;'>Bem-vindo, {usuario}!</h1></div>", unsafe_allow_html=True)
        if perfis:
            st.markdown("<div style='display: flex; align-items: center; gap: 8px; color: #888; margin-bottom: 10px;'><span class='material-symbols-outlined'>group</span><h4>Atletas Salvos</h4></div>", unsafe_allow_html=True)
            for n_salvo in list(perfis.keys()):
                c_b, c_d = st.columns([7.5, 2.5])
                with c_b:
                    if st.button(f"Acessar: {n_salvo.upper()}", key=f"b_{n_salvo}", use_container_width=True):
                        st.session_state.dados_usuario = perfis[n_salvo]["dados"]
                        st.session_state.mensagens = perfis[n_salvo]["mensagens"]
                        st.session_state.etapa = 2
                        st.session_state.scroll_top = True
                        st.rerun()
                with c_d:
                    if st.button("Excluir", key=f"d_{n_salvo}", use_container_width=True):
                        del st.session_state.banco[usuario]["perfis"][n_salvo]
                        salvar_banco(st.session_state.banco)
                        st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("<div style='display: flex; align-items: center; gap: 8px; color: #888; margin-bottom: 10px;'><span class='material-symbols-outlined'>add_box</span><h4>Novo Protocolo</h4></div>", unsafe_allow_html=True)
        with st.form("perfil_usuario"):
            nome = st.text_input("Nome do Atleta", placeholder="Ex: Lucas Barbosa")
            cp, ca = st.columns(2)
            peso = cp.number_input("Peso (kg)", 30.0, 250.0, 75.0)
            altura = ca.number_input("Altura (cm)", 100, 230, 175)
            objetivo = st.selectbox("Objetivo", ["Ganhar Massa Muscular (Hipertrofia)", "Perder Peso (Déficit Calórico)", "Melhorar Performance (Força/Resistência)", "Definição Corporal", "Manutenção da Saúde"])
            nivel = st.selectbox("Nível de Atividade", ["Sedentário", "Levemente Ativo", "Moderadamente Ativo", "Muito Ativo", "Extremamente Ativo"])
            if st.form_submit_button("GERAR PROTOCOLO ELITE", type="primary", use_container_width=True):
                if not nome: exibir_mensagem("Nome necessário.", "warning")
                else:
                    st.session_state.dados_usuario = {"nome": nome, "peso": peso, "altura": altura, "objetivo": objetivo, "nivel": nivel}
                    with st.spinner("Gerando..."):
                        p_mestre = f"Atue como Nutricionista e Personal de Elite. Crie plano para {nome} ({peso}kg, {altura}cm, {nivel}, {objetivo}). # PROTOCOLO: {nome.upper()} ## 1. ANÁLISE METABÓLICA | TMB | GET | Meta | ## 2. PLANO ALIMENTAR | Refeição | Alimento | Macros | Subs | ## 3. TREINO | Exercício | Séries | Reps | Descanso | ## 4. SUPLEMENTAÇÃO | Suplemento | Dose | Hora |"
                        try:
                            res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}", json={"contents": [{"parts": [{"text": p_mestre}]}]}, timeout=40)
                            if res.status_code == 200:
                                txt = res.json()['candidates'][0]['content']['parts'][0]['text']
                                st.session_state.mensagens = [{"role": "assistant", "content": limpar_none(txt)}]
                                # 🟢 GARANTIA DE ESTRUTURA NA GRAVAÇÃO
                                if "perfis" not in st.session_state.banco[usuario]: st.session_state.banco[usuario]["perfis"] = {}
                                st.session_state.banco[usuario]["perfis"][nome] = {"dados": st.session_state.dados_usuario, "mensagens": st.session_state.mensagens}
                                salvar_banco(st.session_state.banco)
                                st.session_state.etapa = 2
                                st.session_state.scroll_top = True
                                st.rerun()
                        except: exibir_mensagem("Erro de conexão.", "error")
        st.markdown("<br><br>", unsafe_allow_html=True); st.divider()
        if st.button("Sair da Conta 🚪", use_container_width=True):
            st.session_state.banco[usuario]["token"] = ""; salvar_banco(st.session_state.banco); st.query_params.clear(); st.session_state.usuario_logado = None; st.session_state.etapa = 0; st.session_state.scroll_top = True; st.rerun()

# ==========================================================
# ETAPA 2: PROTOCOLO E CHAT
# ==========================================================
elif st.session_state.etapa == 2:
    dados = st.session_state.dados_usuario
    nome, usuario = dados["nome"], st.session_state.usuario_logado
    if st.button("Voltar ao Painel"): st.session_state.etapa = 1; st.session_state.mensagens = []; st.session_state.scroll_top = True; st.rerun()
    exibir_mensagem(f"Protocolo de {nome} pronto!", "success")
    c1, c2 = st.columns(2); c1.metric("Atleta", nome); c2.metric("Objetivo", dados["objetivo"].split("(")[0])
    st.divider()
    for m in st.session_state.mensagens:
        if m["role"] == "user": st.markdown(f"<div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'><div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%;'>{m['content']}</div></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div style='margin-bottom: 25px;'>{m['content']}</div>", unsafe_allow_html=True)
    st.divider()
    st.download_button("Baixar PDF", gerar_pdf(st.session_state.mensagens[0]["content"], nome), f"Protocolo_{nome}.pdf", "application/pdf", type="primary", use_container_width=True)
    st.markdown("<br><h3>Central de Dúvidas</h3>", unsafe_allow_html=True)
    if p_duvida := st.chat_input("Dúvida..."):
        st.session_state.mensagens.append({"role": "user", "content": p_duvida})
        st.rerun() # Rerun para mostrar a pergunta e processar a resposta
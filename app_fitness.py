import streamlit as st

# 🟢 OBRIGATÓRIO: Este comando DEVE ser o primeiro do Streamlit na página!
st.set_page_config(page_title="Halter AI", page_icon="logo.png", layout="wide")

import requests
import json
import hashlib
import secrets
import base64
import re
import time
import pandas as pd
import plotly.express as px  
from fpdf import FPDF 

# Configurações iniciais
CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash-lite"

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
        resposta = requests.get(URL_FIRESTORE)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "fields" in dados:
                return {k: conversor_para_python(v) for k, v in dados["fields"].items()}
    except Exception:
        pass
    return {}

def salvar_banco(dados):
    # DICA DE ESCALABILIDADE: Atualmente, isto salva TODOS os utilizadores de uma vez.
    # No futuro, recomendo alterar o Firestore para que cada utilizador seja um Documento 
    # separado. Assim, a gravação será instantânea e consumirá menos banda.
    try:
        campos = {str(k): conversor_para_firestore(v) for k, v in dados.items()}
        payload = {"fields": campos}
        requests.patch(URL_FIRESTORE, json=payload)
    except Exception:
        pass

# --- FUNÇÕES DE SEGURANÇA E UTILIDADE ---
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def gerar_token_sessao():
    return secrets.token_hex(16)

def limpar_para_pdf(texto):
    if not texto: return ""
    texto = texto.replace('"', '').replace('**', '').replace('\r', '')
    substituicoes = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '-', '\u2026': '...',
        '\u00a0': ' ', '\u200b': ''
    }
    for char, sub in substituicoes.items():
        texto = texto.replace(char, sub)
    return texto.encode("latin-1", "ignore").decode("latin-1").strip()

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

def gerador_de_texto(texto):
    for palavra in texto.split(" "):
        yield palavra + " "
        time.sleep(0.03)

# 🟢 OTIMIZAÇÃO: Cache para a leitura do Logo (evita ler o disco toda a hora)
@st.cache_data(show_spinner=False)
def carregar_logo_b64(caminho_imagem):
    try:
        with open(caminho_imagem, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def extrair_json_da_ia(texto):
    match = re.search(r'```json\n(.*?)\n```', texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return None

# 🟢 Motor Aprimorado: Extrai o Título e a Tabela juntos
@st.cache_data(show_spinner=False)
def extrair_tabelas_do_markdown(texto):
    tabelas = []
    linhas = texto.split('\n')
    em_tabela = False
    tabela_atual = []
    ultimo_titulo = ""
    
    for linha in linhas:
        l_strip = linha.strip()
        if l_strip.startswith('|') or l_strip.count('|') >= 2:
            em_tabela = True
            tabela_atual.append(l_strip)
        else:
            if em_tabela:
                tabelas.append((ultimo_titulo, tabela_atual))
                tabela_atual = []
                em_tabela = False
            
            # Limpa formatações para extrair um título limpo
            limpo = re.sub(r'^#+\s*', '', l_strip).replace('**', '').replace(':', ' -').strip()
            # Garante que não é um item de lista, e que não é longo demais
            if limpo and not limpo.startswith(('|', '-', '* ', '•')):
                if len(limpo) < 70:
                    ultimo_titulo = limpo
                    
    if em_tabela and tabela_atual:
        tabelas.append((ultimo_titulo, tabela_atual))
        
    dfs = []
    for titulo, tab in tabelas:
        if len(tab) > 1:
            cols = [c.strip() for c in tab[0].strip('|').split('|')]
            dados = []
            for row in tab[1:]:
                # Filtro Absoluto: Remove as linhas de traços do markdown
                if re.match(r'^[\s\|\-\:]+$', row):
                    continue
                vals = [c.strip() for c in row.strip('|').split('|')]
                if len(vals) < len(cols): vals.extend(['']*(len(cols)-len(vals)))
                elif len(vals) > len(cols): vals = vals[:len(cols)]
                dados.append(vals)
            df = pd.DataFrame(dados, columns=cols)
            dfs.append((titulo, df))
    return dfs

# ==========================================================
# 🟢 CLASSE PDF: DESIGN PREMIUM (BANNER SUPERIOR)
# ==========================================================
class PDF_Elite(FPDF):
    def __init__(self, nome_perfil):
        super().__init__()
        self.nome_perfil = nome_perfil

    def header(self):
        self.set_fill_color(22, 22, 22)
        self.rect(0, 0, 210, 24, 'F')
        
        try:
            self.image("logo.png", 10, 5, 14)
            self.set_x(28)
        except:
            self.set_x(10)
            
        self.set_font("Arial", "B", 13)
        self.set_text_color(255, 255, 255)
        self.cell(0, 14, "HALTER AI - PLANEJAMENTO ", 0, 0, "L")
        
        self.set_font("Arial", "B", 10)
        self.set_text_color(180, 180, 180)
        self.cell(0, 14, f"PERFIL: {self.nome_perfil.upper()}", 0, 1, "R")
        
        self.ln(12) 

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

@st.cache_data(show_spinner=False)
def gerar_pdf(texto_md, nome_perfil):
    texto_limpo = re.sub(r'```json\n.*?\n```', '', texto_md, flags=re.DOTALL)
    
    marcadores = ["## 🧬 1. ANÁLISE METABÓLICA", "## 🧬 1", "1. ANÁLISE METABÓLICA", "# PLANEJAMENTO", "# PLANEJAMENTO"]
    for marcador in marcadores:
        if marcador in texto_limpo:
            texto_limpo = marcador + texto_limpo.split(marcador, 1)[1]
            break
            
    texto_limpo = re.sub(r'# PLANEJAMENTO:? ?' + re.escape(nome_perfil), '', texto_limpo, flags=re.IGNORECASE).strip()
    
    pdf = PDF_Elite(nome_perfil)
    pdf.set_auto_page_break(True, margin=20) 
    pdf.add_page()
    
    linhas = texto_limpo.split("\n") + [""] 
    buffer_tabela = []
    em_tabela = False

    for linha in linhas:
        l_strip = linha.strip()

        eh_linha_tabela = l_strip.startswith('|') or l_strip.count('|') >= 2
        
        if eh_linha_tabela:
            em_tabela = True
            buffer_tabela.append(l_strip)
            continue
        elif em_tabela:
            if buffer_tabela:
                def extrair_celulas(linha_str):
                    s = linha_str.strip()
                    if s.startswith('|'): s = s[1:]
                    if s.endswith('|'): s = s[:-1]
                    return [c.strip().replace('"', '') for c in s.split('|')]

                cols = extrair_celulas(buffer_tabela[0])
                if cols:
                    num_cols = len(cols)
                    if num_cols > 0:
                        w_col = 190 / num_cols
                        
                        def draw_row(dados_linha, eh_cabecalho=False, zebra=False):
                            pdf.set_font("Arial", "B" if eh_cabecalho else "", 10 if eh_cabecalho else 9)
                                
                            max_l = 1
                            for txt in dados_linha:
                                txt_limpo = limpar_para_pdf(txt)
                                cw = pdf.get_string_width(txt_limpo)
                                w_seguro = w_col - 6 
                                if w_seguro <= 0: w_seguro = 1
                                linhas_txt = int(cw / w_seguro) + 1 
                                if linhas_txt > max_l: 
                                    max_l = linhas_txt
                                    
                            alt_linha = (5 * max_l) + 8 
                            
                            if pdf.get_y() + alt_linha > 270:
                                pdf.add_page()
                                
                            y_ini = pdf.get_y()
                            
                            pdf.set_draw_color(220, 220, 220) 
                            if eh_cabecalho:
                                pdf.set_fill_color(35, 35, 35) 
                                pdf.set_text_color(255, 255, 255)
                            else:
                                pdf.set_text_color(40, 40, 40)
                                if zebra:
                                    pdf.set_fill_color(248, 248, 248)
                                else:
                                    pdf.set_fill_color(255, 255, 255)

                            for i, txt in enumerate(dados_linha):
                                x_ini = 10 + (i * w_col)
                                pdf.set_xy(x_ini, y_ini)
                                pdf.cell(w_col, alt_linha, "", 1, 0, "", True)
                                
                                pdf.set_xy(x_ini, y_ini + 4) 
                                txt_limpo = limpar_para_pdf(txt)
                                pdf.multi_cell(w_col, 5, txt_limpo, 0, "C")
                                
                            pdf.set_xy(10, y_ini + alt_linha)

                        draw_row(cols, eh_cabecalho=True)
                        
                        zebra = False
                        for l_tab in buffer_tabela[1:]:
                            if re.match(r'^[\s\|\-\:]+$', l_tab):
                                continue
                            
                            dados = extrair_celulas(l_tab)
                            if len(dados) < num_cols:
                                dados.extend([''] * (num_cols - len(dados)))
                            elif len(dados) > num_cols:
                                dados = dados[:num_cols]
                                
                            draw_row(dados, eh_cabecalho=False, zebra=zebra)
                            zebra = not zebra
                        
            pdf.ln(8)
            buffer_tabela = []
            em_tabela = False

        if not l_strip: 
            pdf.ln(2)
            continue

        l_limpa = l_strip.replace("**", "").replace("* ", "• ")

        if l_strip.startswith('### '):
            pdf.ln(6)
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 6, limpar_para_pdf(l_limpa.replace('### ', '')))
            pdf.ln(1)
        elif l_strip.startswith('## '):
            pdf.ln(10)
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(20, 20, 20)
            
            titulo = l_limpa.replace('## ', '')
            titulo_sem_emoji = re.sub(r'[^\w\s.,-]', '', titulo).strip()
            
            pdf.cell(0, 8, limpar_para_pdf(titulo_sem_emoji), 0, 1, "L")
            
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
        elif l_strip.startswith('# '):
            pass 
        else:
            pdf.set_font("Arial", "", 10.5)
            pdf.set_text_color(50, 50, 50)
            
            if l_limpa.startswith('• '):
                pdf.set_x(15)
                pdf.multi_cell(0, 6, limpar_para_pdf(l_limpa))
            else:
                pdf.multi_cell(0, 6, limpar_para_pdf(l_limpa))

    resultado = pdf.output(dest="S")
    if isinstance(resultado, str):
        return resultado.encode("latin-1", "ignore")
    return bytes(resultado)

# 🟢 CSS CUSTOMIZADO LIMPO E PRECISO
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');

header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton, #MainMenu, footer { display: none !important; }

.block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.stMarkdown table {
    display: block !important; overflow-x: auto !important; white-space: nowrap !important; 
    max-width: 100% !important; width: 100% !important; border-radius: 8px; margin-bottom: 20px;
}

.stButton > button, div[data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
    border-radius: 8px !important; transition: all 0.3s ease; min-height: 45px;
}

div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
    border-color: #1A1A1A !important; box-shadow: 0 0 0 1px #1A1A1A !important;
}

button[data-baseweb="tab"]:hover p, button[data-baseweb="tab"]:focus p, button[data-baseweb="tab"]:active p, button[data-baseweb="tab"][aria-selected="true"] p { 
    color: #1A1A1A !important; font-weight: 600 !important;
}

[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #1A1A1A !important; }
div[data-testid="metric-container"] {
    background-color: rgba(128,128,128,0.02); border: 1px solid rgba(128,128,128,0.1); padding: 10px 15px; border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE ESTADO ---
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
# ETAPA 0: TELA DE LOGIN, CADASTRO E LANDING PAGE
# ==========================================================
if st.session_state.etapa == 0:
    st.markdown("""
<div style="text-align: center; margin-top: 1rem; margin-bottom: 3rem;">
    <span style="display: inline-flex; align-items: center; gap: 6px; background-color: rgba(128,128,128,0.1); border: 1px solid rgba(128,128,128,0.2); padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 1px;">
        <span class="material-symbols-outlined" style="font-size: 16px;">bolt</span> O FUTURO DO TREINAMENTO ESPORTIVO
    </span>
    <h1 style="font-size: 3.5rem; font-weight: 800; margin-top: 1.5rem; line-height: 1.1; letter-spacing: -1px;">
        Transforme o seu corpo com<br>
        <span style="background: -webkit-linear-gradient(45deg, #1A1A1A, #888888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">apenas um prompt</span>
    </h1>
    <p style="font-size: 1.2rem; color: #888; max-width: 600px; margin: 1.5rem auto; line-height: 1.6;">
        Treinos, dieta e suplementação milimetricamente calculados por IA. 
        Sem achismos. Sem treinos genéricos. Apenas resultados.
    </p>
</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        img_b64 = carregar_logo_b64("logo.png")
        if img_b64:
            st.markdown(f'<div style="display: flex; justify-content: center; margin-bottom: 20px;"><img src="data:image/png;base64,{img_b64}" width="140"></div>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta Nova"])
        
        with tab1:
            with st.form("form_login"):
                usuario_login = st.text_input("Utilizador ou E-mail")
                senha_login = st.text_input("Palavra-passe", type="password")
                manter_conectado = st.checkbox("Manter sessão iniciada") 
                btn_login = st.form_submit_button("Acessar a Plataforma", type="primary", use_container_width=True)
                
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
                        exibir_mensagem("Credenciais incorretas.", "error")
                        
        with tab2:
            with st.form("form_cadastro"):
                novo_usuario = st.text_input("Escolha um Nome de Utilizador")
                novo_email = st.text_input("Digite o seu E-mail")
                nova_senha = st.text_input("Crie uma Palavra-passe", type="password")
                confirma_senha = st.text_input("Confirme a Palavra-passe", type="password")
                btn_cadastro = st.form_submit_button("Criar Conta", type="primary", use_container_width=True)
                
                if btn_cadastro:
                    email_em_uso = any(dados.get("email") == novo_email for dados in st.session_state.banco.values())
                    
                    if not novo_usuario or not novo_email or not nova_senha or not confirma_senha:
                        exibir_mensagem("Preencha todos os campos!", "warning")
                    elif nova_senha != confirma_senha:
                        exibir_mensagem("As palavras-passe não coincidem.", "warning")
                    elif novo_usuario in st.session_state.banco:
                        exibir_mensagem("Utilizador já em uso!", "warning")
                    elif email_em_uso:
                        exibir_mensagem("E-mail já registado!", "warning")
                    else:
                        st.session_state.banco[novo_usuario] = {
                            "email": novo_email, "senha": criptografar_senha(nova_senha), "token": "", "perfis": {}
                        }
                        salvar_banco(st.session_state.banco)
                        exibir_mensagem("Conta criada com sucesso!", "success")

# ==========================================================
# ETAPA 1: PAINEL DO USUÁRIO (PERFIS + NOVO)
# ==========================================================
elif st.session_state.etapa == 1:
    
    usuario = st.session_state.usuario_logado
    perfis_do_usuario = st.session_state.banco[usuario]["perfis"]
    
    col_esquerda, col_centro, col_direita = st.columns([1, 1.5, 1])
    
    with col_centro:
        st.markdown(f"""
<div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
    <p style="color: #888; font-size: 0.9rem; font-weight: 600; letter-spacing: 1px; margin-bottom: 0;">PAINEL DE CONTROLO</p>
    <h1 style="font-size: 2.2rem; font-weight: 800; margin-top: 0;">Bem-vindo, {usuario}!</h1>
</div>
        """, unsafe_allow_html=True)
        
        if perfis_do_usuario:
            st.markdown("""<div style='display: flex; align-items: center; gap: 8px; color: #888; margin-bottom: 10px;'><span class='material-symbols-outlined'>group</span><h4 style='margin: 0;'>Planejamentos Criados</h4></div>""", unsafe_allow_html=True)
            
            colunas_grid = st.columns(2)
            
            for i, nome_salvo in enumerate(list(perfis_do_usuario.keys())):
                col_atual = colunas_grid[i % 2] 
                
                with col_atual:
                    with st.container(border=True): 
                        
                        dados_salvos = perfis_do_usuario[nome_salvo].get("dados", {})
                        obj_salvo = dados_salvos.get("objetivo", "Não definido").split("(")[0].strip()
                        peso_salvo = dados_salvos.get("peso", "-")
                        
                        imc_salvo = "-"
                        if "peso" in dados_salvos and "altura" in dados_salvos:
                            try:
                                imc_calc = dados_salvos["peso"] / ((dados_salvos["altura"] / 100) ** 2)
                                imc_salvo = f"{imc_calc:.1f}"
                            except:
                                pass

                        st.markdown(f"""
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
    <span class="material-symbols-outlined" style="color: #1A1A1A; font-size: 1.4rem;">person</span>
    <h4 style="margin: 0; color: #1A1A1A; font-weight: 700;">{nome_salvo.upper()}</h4>
</div>
<div style="color: #666; font-size: 0.85rem; margin-bottom: 15px; display: flex; flex-direction: column; gap: 6px;">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span class="material-symbols-outlined" style="font-size: 16px;">ads_click</span>
        <span><b>Objetivo:</b> {obj_salvo}</span>
    </div>
    <div style="display: flex; align-items: center; gap: 8px;">
        <span class="material-symbols-outlined" style="font-size: 16px;">monitor_weight</span>
        <span><b>Peso:</b> {peso_salvo}kg</span>
        <span style="margin: 0 4px; color: #ddd;">|</span>
        <span class="material-symbols-outlined" style="font-size: 16px;">analytics</span>
        <span><b>IMC:</b> {imc_salvo}</span>
    </div>
</div>
                        """, unsafe_allow_html=True)
                        
                        c_btn, c_del = st.columns([4, 1]) 
                        with c_btn:
                            if st.button("Abrir Painel", key=f"btn_{nome_salvo}", type="primary", use_container_width=True):
                                st.session_state.dados_usuario = perfis_do_usuario[nome_salvo]["dados"]
                                st.session_state.mensagens = perfis_do_usuario[nome_salvo]["mensagens"]
                                st.session_state.etapa = 2
                                st.rerun()
                        with c_del:
                            if st.button(" ", icon=":material/delete:", key=f"del_{nome_salvo}", help="Excluir Perfil", use_container_width=True):
                                del st.session_state.banco[usuario]["perfis"][nome_salvo]
                                salvar_banco(st.session_state.banco)
                                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""<div style='display: flex; align-items: center; gap: 8px; color: #888; margin-bottom: 10px;'><span class='material-symbols-outlined'>add_box</span><h4 style='margin: 0;'>Novo Planejamento</h4></div>""", unsafe_allow_html=True)
        else:
            exibir_mensagem("Nenhum perfil registado ainda.", "info")
        
        with st.form("perfil_usuario"):
            nome = st.text_input("Nome do Perfil", placeholder="Ex: Lucas Barbosa")
            
            c_idade, c_sexo = st.columns(2)
            with c_idade: idade = st.number_input("Idade", min_value=12, max_value=100, value=25, step=1)
            with c_sexo: sexo = st.selectbox("Sexo", ["Masculino", "Feminino", "Outro"])

            c_peso, c_altura = st.columns(2)
            with c_peso: peso = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
            with c_altura: altura = st.number_input("Altura (cm)", min_value=100, max_value=230, value=175, step=1)
            
            alergias = st.text_input("Alergias ou Restrições Alimentares", placeholder="Ex: Nenhuma, Intolerância à lactose, Alergia a amendoim")

            objetivo = st.selectbox("Objetivo Principal", ["Ganhar Massa Muscular (Hipertrofia)", "Perder Peso (Déficit Calórico)", "Melhorar Performance (Força/Resistência)", "Definição Corporal", "Manutenção da Saúde"])
            nivel_atividade = st.selectbox("Nível de Atividade Diária", ["Sedentário (Trabalho de escritório, sem exercícios)", "Levemente Ativo (1 a 3 dias de exercício/semana)", "Moderadamente Ativo (3 a 5 dias de exercício/semana)", "Muito Ativo (6 a 7 dias de exercício intenso/semana)", "Extremamente Ativo (Atleta profissional, treinos duplos)"])

            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button(label="GERAR PLANEJAMENTO", type="primary", use_container_width=True)

        if submit_button:
            if not nome:
                exibir_mensagem("Identificação necessária.", "warning")
            elif nome in perfis_do_usuario:
                exibir_mensagem(f"O perfil '{nome}' já existe!", "warning")
            else:
                st.session_state.dados_usuario = {
                    "nome": nome, "idade": idade, "sexo": sexo, "peso": peso, "altura": altura, 
                    "alergias": alergias if alergias else "Nenhuma", "objetivo": objetivo, "nivel": nivel_atividade
                }
                
                with st.spinner("Analisando dados e estruturando o planejamento..."):
                    
                    prompt_mestre = f"""
                    Atue como um Nutricionista Esportivo Clínico e Personal Trainer de extrema qualidade. 
                    Crie um planejamento irretocável e personalizado para o(a) {nome}. Leve em consideração suas características.
                    Idade: {idade} anos | Sexo: {sexo}
                    Peso: {peso}kg | Altura: {altura}cm | Nível: {nivel_atividade} | Objetivo: {objetivo}
                    Alergias/Restrições: {alergias if alergias else 'Nenhuma'}

                    # PLANEJAMENTO: {nome.upper()}

                    ## 🧬 1. ANÁLISE METABÓLICA
                    Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
                    | Taxa Metabólica Basal (Mifflin-St Jeor)| Gasto Energético Total | Meta Calórica Alvo |

                    ## 🥗 2. PLANO ALIMENTAR
                    Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo (Seja variado na criação do plano, não monte algo genérico e respeite as restrições alimentares mencionadas):
                    | Refeição(Almoço, janta, etc) | Alimento Principal | Macronutrientes | Substituição |
                    
                    ## ⚡ 3. PLANILHA DE TREINAMENTO
                    Defina uma divisão semanal inteligente (ex:ABCDE, ABC, AB, Fullbody) com base no objetivo e sexo.
                    Para CADA DIA de treino, crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:

                    | Exercício | Séries | Repetições | Descanso |

                    ## 💊 4. SUPLEMENTAÇÃO
                    | Suplemento | Dosagem Diária | Horário |

                    INSTRUÇÃO OBRIGATÓRIA PARA DASHBOARD: No final absoluto da sua resposta, insira APENAS UM bloco de código json contendo as metas financeiras numéricas diárias, seguindo estritamente esta estrutura:
                    ```json
                    {{
                        "calorias": 0,
                        "proteinas_g": 0,
                        "carboidratos_g": 0,
                        "gorduras_g": 0,
                        "tmb": 0,
                        "gasto_total": 0,
                        "agua_ml": 0,
                        "passos": 0
                    }}
                    ```
                    Substitua os zeros pelos valores calculados em números inteiros (apenas números). Estime a água (ex: 35ml a 40ml por kg) e uma boa meta de passos diários baseada no objetivo.
                    """

                    url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                    payload = {"contents": [{"parts": [{"text": prompt_mestre}]}]}
                    
                    try:
                        resposta = requests.post(url, json=payload, timeout=30)
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
                            exibir_mensagem("Erro no Servidor. Tente novamente.", "error")
                    except Exception as e:
                        exibir_mensagem("Erro de conexão.", "error")
  
        st.divider()
        c_vazia1, c_botao_sair, c_vazia2 = st.columns([3, 4, 3])
        with c_botao_sair:
            if st.button("Sair da Plataforma", use_container_width=True, icon=":material/logout:"):
                if "token" in st.session_state.banco[usuario]:
                    st.session_state.banco[usuario]["token"] = ""
                    salvar_banco(st.session_state.banco)
                st.query_params.clear()
                st.session_state.usuario_logado = None
                st.session_state.etapa = 0
                st.rerun()

# ==========================================================
# ETAPA 2: PÁGINA DO PLANO GERADO E CHAT DA IA
# ==========================================================
elif st.session_state.etapa == 2:
    
    usuario = st.session_state.usuario_logado
    dados = st.session_state.dados_usuario
    
    nome = dados["nome"]
    idade = dados.get("idade", "-")
    sexo = dados.get("sexo", "-")
    peso = dados["peso"]
    altura = dados["altura"]
    alergias = dados.get("alergias", "Nenhuma")
    objetivo_curto = dados["objetivo"].split("(")[0].strip()
    imc = peso / ((altura / 100) ** 2)

    col_voltar, col_vazia = st.columns([4, 6])
    with col_voltar:
        if st.button("Voltar ao Painel", icon=":material/arrow_back:"):
            st.session_state.etapa = 1
            st.rerun()

    plano_atual = ""
    for msg in reversed(st.session_state.mensagens):
        if msg["role"] == "assistant" and "## 🧬" in msg.get("content", ""):
            plano_atual = msg["content"]
            break
    if not plano_atual and st.session_state.mensagens:
        plano_atual = st.session_state.mensagens[0]["content"]

    tabelas_extraidas = extrair_tabelas_do_markdown(plano_atual)
    dados_json = extrair_json_da_ia(plano_atual)

    tab_dash, tab_chat = st.tabs([":material/analytics: DASHBOARD DE ESTATÍSTICAS", ":material/forum: CHAT & PLANEJAMENTO COMPLETO"])

    with tab_dash:
        st.markdown(f"<h2>Painel de Performance: {nome.upper()}</h2>", unsafe_allow_html=True)
        
        st.markdown(f"""
<div style="background: #ffffff; border-radius: 16px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #eaeaea; margin-top: 25px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; gap: 20px; text-align: center;">
    <div style="flex: 1; min-width: 150px;">
        <p style="margin: 0 0 5px 0; font-size: 0.8rem; color: #888; font-weight: 700; text-transform: uppercase;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: 16px; margin-right: 5px;">flag</span>Objetivo Principal</p>
        <p style="margin: 0; font-size: 1.3rem; font-weight: 800; color: #1A1A1A;">{objetivo_curto}</p>
    </div>
    <div style="width: 1px; height: 50px; background-color: #ddd; flex-shrink: 0;"></div>
    <div style="flex: 1; min-width: 150px;">
        <p style="margin: 0 0 5px 0; font-size: 0.8rem; color: #888; font-weight: 700; text-transform: uppercase;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: 16px; margin-right: 5px;">local_fire_department</span>Calorias Diárias</p>
        <p style="margin: 0; font-size: 1.3rem; font-weight: 800; color: #1A1A1A;">{dados_json.get('calorias', '0') if dados_json else '0'} kcal</p>
    </div>
    <div style="width: 1px; height: 50px; background-color: #ddd; flex-shrink: 0;"></div>
    <div style="flex: 1; min-width: 150px;">
        <p style="margin: 0 0 5px 0; font-size: 0.8rem; color: #888; font-weight: 700; text-transform: uppercase;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: 16px; margin-right: 5px;">water_drop</span>Hidratação Alvo</p>
        <p style="margin: 0; font-size: 1.3rem; font-weight: 800; color: #1A1A1A;">{dados_json.get('agua_ml', '0') if dados_json else '0'} ml</p>
    </div>
</div>
        """, unsafe_allow_html=True)
            
        if dados_json:
            calorias = int(dados_json.get('calorias', 0))
            gasto_total = int(dados_json.get('gasto_total', 0))
            
            if calorias > 0 and gasto_total > 0:
                diferenca = calorias - gasto_total
                
                if diferenca < -100:
                    ritmo_perda = abs(diferenca) * 7 / 7700
                    texto_destaque = f"Perda de {ritmo_perda:.2f} kg por semana"
                    texto_secundario = "A IA projetou este défice calórico para que atinja resultados visíveis preservando a massa magra."
                    icone_projecao = "trending_down"
                    cor_icone = "#e74c3c" 
                elif diferenca > 100:
                    ritmo_ganho = diferenca * 7 / 7700
                    texto_destaque = f"Ganho de {ritmo_ganho:.2f} kg por semana"
                    texto_secundario = "O seu plano tem um superávit calórico otimizado para o ganho de massa muscular sólida."
                    icone_projecao = "trending_up"
                    cor_icone = "#2ecc71" 
                else:
                    texto_destaque = "Recomposição Corporal (Manutenção)"
                    texto_secundario = "A IA calculou calorias estáveis para perder gordura e ganhar músculo em simultâneo."
                    icone_projecao = "balance"
                    cor_icone = "#f39c12" 

                st.markdown(f"""
<div style="background: linear-gradient(135deg, #ffffff 0%, #f7f9fa 100%); border-radius: 16px; padding: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.04); margin-top: 25px; margin-bottom: 30px; display: flex; align-items: center; gap: 24px; transition: transform 0.3s ease;">
    <div style="background-color: #1A1A1A; color: {cor_icone}; border-radius: 50%; width: 70px; height: 70px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
        <span class="material-symbols-outlined" style="font-size: 38px;">{icone_projecao}</span>
    </div>
    <div>
        <p style="margin: 0; font-size: 0.9rem; color: #888; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">Projeção Halter AI</p>
        <h3 style="margin: 5px 0 5px 0; font-size: 1.8rem; font-weight: 800; color: #1A1A1A;">
            {texto_destaque}
        </h3>
        <p style="margin: 0; font-size: 1rem; color: #666; line-height: 1.4;">
            {texto_secundario}
        </p>
    </div>
</div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        col_grafico, col_dieta = st.columns([1, 2.5])
        
        with col_grafico:
            st.markdown("#### Distribuição de Macros")
            if dados_json and "proteinas_g" in dados_json:
                df_macros = pd.DataFrame({
                    "Macro": ["Proteína", "Carbo", "Gordura"],
                    "Gramas": [dados_json.get("proteinas_g", 0), dados_json.get("carboidratos_g", 0), dados_json.get("gorduras_g", 0)]
                })
                fig = px.pie(df_macros, values='Gramas', names='Macro', hole=0.55, 
                             color_discrete_sequence=['#1A1A1A', '#555555', '#A0A0A0'])
                fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=14)
                fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Gráfico numérico não disponível para planos antigos.")

        with col_dieta:
            st.markdown("#### Plano Alimentar Completo")
            # Busca a tabela de dieta
            df_dieta = next((df for titulo, df in tabelas_extraidas if any("refeição" in c.lower() or "alimento" in c.lower() for c in df.columns)), None)
            
            if df_dieta is not None:
                # 🟢 A MÁGICA AQUI: Remove todos os asteriscos da tabela inteira de uma vez
                df_dieta = df_dieta.replace(r'\*\*', '', regex=True)
                
                st.dataframe(df_dieta, use_container_width=True, hide_index=True)
                
            elif len(tabelas_extraidas) > 1:
                # Pega a segunda tabela caso a primeira não seja a dieta, limpando também os asteriscos
                df_reserva = tabelas_extraidas[1][1].replace(r'\*\*', '', regex=True)
                st.dataframe(df_reserva, use_container_width=True, hide_index=True)
            else:
                st.warning("A gerar tabelas estruturadas...")

        st.divider()

        col_treino, col_suple = st.columns([2, 1])
        
        with col_treino:
            st.markdown("#### Planilha de Treinamento")
            treinos_encontrados = [(titulo, df) for titulo, df in tabelas_extraidas if any("exercício" in c.lower() or "séries" in c.lower() for c in df.columns)]
            
            if treinos_encontrados:
                nomes_opcoes = []
                for i, (titulo, df) in enumerate(treinos_encontrados):
                    nome_opcao = titulo if titulo else f"Treino {i+1}"
                    if nomes_opcoes.count(nome_opcao) > 0:
                        nome_opcao = f"{nome_opcao} ({i+1})"
                    nomes_opcoes.append(nome_opcao)
                
                treino_selecionado = st.selectbox("Selecione o Dia / Treino:", nomes_opcoes)
                
                idx_treino = nomes_opcoes.index(treino_selecionado)
                df_exibir = treinos_encontrados[idx_treino][1]
                
                st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            else:
                st.info("Visualização de treino indisponível.")

        with col_suple:
            st.markdown("#### Suplementação")
            df_suple = next((df for titulo, df in tabelas_extraidas if any("suplemento" in c.lower() for c in df.columns)), None)
            
            if df_suple is not None:
                # 🟢 LIMPEZA: Remove os asteriscos de negrito do Markdown
                df_suple = df_suple.replace(r'\*\*', '', regex=True)
                st.dataframe(df_suple, use_container_width=True, hide_index=True)
            else:
                st.info("Sem suplementos estruturados.")
                
            st.markdown("#### Índice de Massa Corporal (IMC)")
            
            if imc < 18.5:
                status_imc = "Baixo Peso"
                cor_imc = "#f1c40f"
                posicao_progresso = 10
            elif 18.5 <= imc < 25:
                status_imc = "Peso Normal (Saudável)"
                cor_imc = "#2ecc71"
                posicao_progresso = 40
            elif 25 <= imc < 30:
                status_imc = "Sobrepeso"
                cor_imc = "#e67e22"
                posicao_progresso = 70
            else:
                status_imc = "Obesidade"
                cor_imc = "#e74c3c"
                posicao_progresso = 90

            st.markdown(f"""
<div style="background: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eaeaea; box-shadow: 0 4px 6px rgba(0,0,0,0.02); text-align: center; margin-top: 15px;">
    <p style="margin: 0; font-size: 0.85rem; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Seu Resultado</p>
    <h2 style="margin: 5px 0 10px 0; font-size: 3rem; font-weight: 800; color: #1A1A1A;">{imc:.1f}</h2>
    <div style="width: 100%; height: 12px; background: linear-gradient(to right, #f1c40f 0%, #2ecc71 40%, #e67e22 70%, #e74c3c 100%); border-radius: 6px; position: relative; margin-bottom: 10px;">
        <div style="width: 4px; height: 20px; background-color: #1A1A1A; border-radius: 2px; position: absolute; left: calc({posicao_progresso}% - 2px); top: -4px; border: 2px solid #fff;"></div>
    </div>
    <div style="display: inline-block; background-color: {cor_imc}; color: #fff; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; margin-top: 5px;">
        {status_imc.upper()}
    </div>
</div>
""", unsafe_allow_html=True)
                
        st.divider()
        pdf_final = gerar_pdf(plano_atual, nome)
        st.download_button(
            label="Baixar Relatório Completo (PDF Premium)",
            data=pdf_final,
            file_name=f"Relatorio_Performance_{nome.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

    with tab_chat:
        
        with st.expander("VER PLANO COMPLETO EM TEXTO (MARKDOWN)", expanded=False):
            texto_exibicao = re.sub(r'```json\n.*?\n```', '', limpar_none(plano_atual), flags=re.DOTALL)
            st.markdown(texto_exibicao)

        pdf_final = gerar_pdf(plano_atual, nome)
        st.download_button(
            label="Baixar Relatório Completo (PDF Premium)",
            data=pdf_final,
            file_name=f"Relatorio_Performance_{nome.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )    
        st.markdown("""
<div style='display: flex; align-items: center; gap: 8px; margin-top: 15px; margin-bottom: 5px;'>
    <span class='material-symbols-outlined'>forum</span> 
    <h3 style='margin: 0;'>Assistente de Ajustes</h3>
</div>
<p style="color: #888; font-size: 0.9rem; margin-bottom: 10px;">
    Peça mudanças no treino ou dieta. O Dashboard <b>será atualizado automaticamente</b>.
</p>
        """, unsafe_allow_html=True)
        
        c_btn1, c_btn2, c_btn3, c_btn_limpar = st.columns([1.5, 1.5, 1.5, 1])
        acao_rapida = None
        
        if c_btn1.button("Tornar Dieta Vegana", icon=":material/eco:", use_container_width=True): acao_rapida = "Altere todo o plano alimentar para uma dieta estritamente vegana, garantindo o aporte de proteínas."
        if c_btn2.button("Variar Refeições", icon=":material/sync:", use_container_width=True): acao_rapida = "Mude as opções de almoço e jantar para opções completamente diferentes das atuais."
        if c_btn3.button("Treino mais Curto", icon=":material/timer:", use_container_width=True): acao_rapida = "Ajuste o treino para que dure no máximo 45 minutos (menos exercícios ou métodos avançados)."
        
        if c_btn_limpar.button("Limpar Chat", icon=":material/delete:", use_container_width=True):
            if len(st.session_state.mensagens) > 0:
                st.session_state.mensagens = [st.session_state.mensagens[0]]
                st.session_state.banco[usuario]["perfis"][nome]["mensagens"] = st.session_state.mensagens
                salvar_banco(st.session_state.banco)
            st.rerun()

        st.divider()

        chat_container = st.container()

        with chat_container:
            for msg in st.session_state.mensagens:
                conteudo = limpar_none(msg.get("content"))
                if msg.get("role") == "assistant" and "## 🧬" in conteudo:
                    continue 
                
                if msg.get("role") == "user":
                    st.markdown(f"""<div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'><div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%; font-family: sans-serif; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>{conteudo}</div></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
                    st.markdown(conteudo)
                    st.markdown("</div>", unsafe_allow_html=True)
        
        prompt_duvida = st.chat_input("Ex: Troque o meu jantar por uma opção vegana...")
        comando_final = acao_rapida if acao_rapida else prompt_duvida
        
        if comando_final:
            st.session_state.mensagens.append({"role": "user", "content": comando_final})
            st.session_state.banco[usuario]["perfis"][nome]["mensagens"] = st.session_state.mensagens
            salvar_banco(st.session_state.banco)
            st.rerun() 

        if st.session_state.mensagens and st.session_state.mensagens[-1]["role"] == "user":
            
            with chat_container:
                with st.spinner("O Treinador está a reformular o seu planejamento..."):
                    comando_usuario = st.session_state.mensagens[-1]["content"]
                    
                    prompt_duvida_completo = f"""Plano Atual do Perfil:
{plano_atual}

Mensagem do Usuário: {comando_usuario}

REGRA DE ATUALIZAÇÃO DO DASHBOARD: 
Se o usuário estiver pedindo QUALQUER ALTERAÇÃO na dieta, treino ou suplementos, VOCÊ DEVE REESCREVER O PLANO COMPLETO aplicando as mudanças solicitadas. Mantenha estritamente a mesma estrutura de marcação (## 🧬, ## 🥗, etc) para que as tabelas sejam lidas.
MUITO IMPORTANTE: Se você reescrever o plano, VOCÊ DEVE INCLUIR o bloco ```json``` no final com os dados numéricos atualizados para o sistema renderizar os gráficos (inclua metas de agua_ml e passos também).
Se for APENAS uma dúvida, responda normalmente de forma curta, sem reescrever o plano."""
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                    payload = {"contents": [{"parts": [{"text": prompt_duvida_completo}]}]}
                    
                    try:
                        resposta = requests.post(url, json=payload, timeout=45) 
                        
                        if resposta.status_code == 200:
                            resposta_data = resposta.json()
                            texto_ia_duvida = resposta_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                            texto_ia_duvida = limpar_none(texto_ia_duvida)
                            
                            if "## 🧬" not in texto_ia_duvida:
                                st.write_stream(gerador_de_texto(texto_ia_duvida))
                            else:
                                # 🟢 OTIMIZAÇÃO: Usando o TOAST nativo do Streamlit ao invés de Sleep() que congelava a aplicação
                                st.toast("Plano atualizado com sucesso! Confira o Dashboard.", icon="✅")
                                
                            st.session_state.mensagens.append({"role": "assistant", "content": texto_ia_duvida})
                            st.session_state.banco[usuario]["perfis"][nome]["mensagens"] = st.session_state.mensagens
                            salvar_banco(st.session_state.banco)
                            
                            st.rerun() 
                        else:
                            st.error(f"Erro {resposta.status_code}. Tente novamente.")
                    except Exception as e:
                        st.error("Erro de ligação.")
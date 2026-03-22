import streamlit as st
import requests
import json
import os
import hashlib
import secrets
from fpdf import FPDF # 🟢 IMPORT: Biblioteca para gerar o PDF

# Configurações iniciais
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

# 🟢 CLASSE DO PDF ELITE (Cabeçalhos, Rodapés e Design Premium)
class PDF_Elite(FPDF):
    def __init__(self, nome_atleta):
        super().__init__()
        self.nome_atleta = nome_atleta

    def header(self):
        # Linha no topo de toda página
        self.set_font("Arial", "B", 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, "PROTOCOLO DE ELITE", 0, 0, "L")
        self.cell(0, 10, f"Atleta: {self.nome_atleta}", 0, 1, "R")
        self.set_draw_color(28, 131, 225)
        self.set_line_width(0.5)
        self.line(10, 18, 200, 18)
        self.ln(5)

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
    _ = pdf.set_text_color(28, 131, 225) 
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
                # Função robusta para extrair células mesmo que estejam vazias
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
                                
                            # 1. Calcula a altura necessária baseada no maior texto
                            max_l = 1
                            for txt in dados_linha:
                                txt_limpo = limpar_para_pdf(txt)
                                cw = pdf.get_string_width(txt_limpo)
                                w_seguro = w_col - 4 # Desconta padding lateral
                                if w_seguro <= 0: w_seguro = 1
                                linhas_txt = int(cw / w_seguro) + 1 
                                if linhas_txt > max_l: 
                                    max_l = linhas_txt
                                    
                            alt_linha = (5 * max_l) + 4 # 5mm por linha de texto + 4mm de padding
                            
                            if pdf.get_y() + alt_linha > 275:
                                _ = pdf.add_page()
                                
                            y_ini = pdf.get_y()
                            
                            # 2. Configura as cores
                            if eh_cabecalho:
                                _ = pdf.set_fill_color(28, 131, 225)
                                _ = pdf.set_text_color(255, 255, 255)
                            else:
                                _ = pdf.set_text_color(40, 40, 40)
                                if zebra:
                                    _ = pdf.set_fill_color(245, 245, 245)
                                else:
                                    _ = pdf.set_fill_color(255, 255, 255)

                            # 3. Desenha os blocos com text wrap
                            for i, txt in enumerate(dados_linha):
                                x_ini = 10 + (i * w_col)
                                _ = pdf.set_xy(x_ini, y_ini)
                                _ = pdf.cell(w_col, alt_linha, "", 1, 0, "", True)
                                
                                _ = pdf.set_xy(x_ini, y_ini + 2) # 2mm de margem superior interna
                                txt_limpo = limpar_para_pdf(txt)
                                _ = pdf.multi_cell(w_col, 5, txt_limpo, 0, "C")
                                
                            _ = pdf.set_xy(10, y_ini + alt_linha)

                        # Desenha cabeçalho
                        draw_row(cols, eh_cabecalho=True)
                        
                        # Desenha resto
                        zebra = False
                        for l_tab in buffer_tabela[1:]:
                            if '---' in l_tab: continue
                            dados = extrair_celulas(l_tab)
                            
                            # Força a linha ter as mesmas colunas do cabeçalho preenchendo vazios
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

        # PROCESSA TÍTULOS E TEXTO NORMAL (Limpando o negrito sujo)
        l_limpa = l_strip.replace("**", "").replace("* ", "- ")

        if l_strip.startswith('### '):
            _ = pdf.ln(2)
            _ = pdf.set_font("Arial", "B", 12)
            _ = pdf.set_text_color(40, 40, 40)
            _ = pdf.multi_cell(0, 7, limpar_para_pdf(l_limpa.replace('### ', '')))
        elif l_strip.startswith('## '):
            _ = pdf.ln(4)
            _ = pdf.set_font("Arial", "B", 14)
            _ = pdf.set_text_color(28, 131, 225)
            _ = pdf.multi_cell(0, 8, limpar_para_pdf(l_limpa.replace('## ', '')))
        elif l_strip.startswith('# '):
            _ = pdf.ln(6)
            _ = pdf.set_font("Arial", "B", 18)
            _ = pdf.set_text_color(28, 131, 225)
            _ = pdf.multi_cell(0, 10, limpar_para_pdf(l_limpa.replace('# ', '')))
            _ = pdf.set_draw_color(28, 131, 225)
            _ = pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            _ = pdf.ln(2)
        else:
            _ = pdf.set_font("Arial", "", 10)
            _ = pdf.set_text_color(60, 60, 60)
            
            # Reconhece "Bullet Points" e dá margem elegante
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
st.set_page_config(page_title="Fitness AI", page_icon="⚡", layout="wide")

# --- CSS CUSTOMIZADO COM REGRAS ESPECÍFICAS PARA CELULAR E TABELAS ESTILO CHATGPT ---
st.markdown("""
    <style>
    [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton { display: none !important; visibility: hidden !important; }
    header { background-color: transparent !important; box-shadow: none !important; }
    #MainMenu, footer { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    /* Configuração Original (PC) */
    .block-container { padding-top: 4rem !important; margin-top: 2rem !important; }
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1); border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 10% 5% 10%; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    
    /* BLOQUEIO DE SCROLL HORIZONTAL NA PÁGINA INTEIRA */
    .stApp { overflow-x: hidden; }

    /* 🟢 COMPORTAMENTO DE TABELA ESTILO CHATGPT */
    .stMarkdown table {
        display: block !important;
        overflow-x: auto !important;
        white-space: nowrap !important; /* Impede que a tabela fique amassada */
        max-width: 100% !important;
        -webkit-overflow-scrolling: touch; /* Scroll suave no celular */
        border-radius: 8px; 
    }
    
    /* Garante que os textos fora da tabela quebrem linha e não estiquem a página */
    .stMarkdown p, .stMarkdown li {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* 📱 OTIMIZAÇÕES EXCLUSIVAS PARA CELULAR */
    @media (max-width: 768px) {
        .block-container { 
            padding-top: 1.5rem !important; 
            margin-top: 0 !important;
            padding-left: 1rem !important; 
            padding-right: 1rem !important;
        }
        input, select, textarea { font-size: 16px !important; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            min-height: 50px !important;
        }
        div[data-testid="metric-container"] { padding: 15px !important; }
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
# ETAPA 0: TELA DE LOGIN E CADASTRO
# ==========================================================
if st.session_state.etapa == 0:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("⚡ Treinador Digital")
        st.markdown("Bem-vindo à plataforma de elite. Faça login ou crie sua conta.")
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta Nova"])
        
        with tab1:
            with st.form("form_login"):
                usuario_login = st.text_input("Usuário ou E-mail")
                senha_login = st.text_input("Senha", type="password")
                manter_conectado = st.checkbox("Mantenha-me conectado") 
                btn_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                
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
    
    # 🟢 NOVO: RENDERIZAÇÃO ESTILO CHATGPT (Sem st.chat_message)
    for msg in st.session_state.mensagens:
        conteudo = limpar_none(msg.get("content"))
        role = msg.get("role")
        
        if role == "user":
            # Bolha de usuário alinhada à direita e com fundo cinza claro, estilo ChatGPT
            st.markdown(f"""
                <div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'>
                    <div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%; font-family: sans-serif; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>
                        {conteudo}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            # Resposta da IA colada à esquerda (sem quadradinhos limitadores)
            st.markdown(f"<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
            st.markdown(conteudo)
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    plano_principal = limpar_none(st.session_state.mensagens[0].get("content")) if st.session_state.mensagens else ""
    
    # Gera o PDF guardando em variável
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
        
        # 1. Adiciona a dúvida do usuário na memória
        st.session_state.mensagens.append({"role": "user", "content": prompt_duvida})
        
        # 2. Exibe imediatamente a bolha do usuário à direita
        st.markdown(f"""
            <div style='display: flex; justify-content: flex-end; margin-bottom: 25px;'>
                <div style='background-color: #f4f4f4; color: #0d0d0d; padding: 12px 18px; border-radius: 18px 18px 0px 18px; max-width: 85%; font-family: sans-serif; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);'>
                    {prompt_duvida}
                </div>
            </div>
        """, unsafe_allow_html=True)
            
        # 3. Faz a requisição sem o quadradinho da IA
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
                    
                    # Exibe a resposta pura, colada à esquerda
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
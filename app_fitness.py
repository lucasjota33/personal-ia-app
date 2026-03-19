import streamlit as st
import requests
import json
import os
import hashlib
import secrets
from fpdf import FPDF # 🟢 NOVO IMPORT: Biblioteca para gerar o PDF

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

# 🟢 NOVA FUNÇÃO: MOTOR DE GERAR PDF
def gerar_pdf(texto_md, nome_atleta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cabeçalho do PDF
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Protocolo Elite - {nome_atleta}", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    
    # O FPDF tem limitações com UTF-8 e emojis. 
    # O comando abaixo limpa símbolos complexos, mas preserva os acentos (latin-1)
    texto_limpo = texto_md.encode("latin-1", "ignore").decode("latin-1")
    
    # Escreve o texto linha por linha
    for linha in texto_limpo.split("\n"):
        pdf.multi_cell(0, 7, txt=linha)
        
    # Converte o PDF para um formato que o botão do Streamlit consiga baixar
    resultado = pdf.output(dest="S")
    if isinstance(resultado, str):
        return resultado.encode("latin-1")
    return bytes(resultado)


# Configuração da Página
st.set_page_config(page_title="Fitness AI", page_icon="⚡", layout="wide")

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton { display: none !important; visibility: hidden !important; }
    header { background-color: transparent !important; box-shadow: none !important; }
    #MainMenu, footer { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding-top: 4rem !important; margin-top: 2rem !important; }
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1); border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 10% 5% 10%; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
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
                    - Taxa Metabólica Basal (Mifflin-St Jeor)
                    - Gasto Energético Total
                    - Meta Calórica Alvo

                    ## 2. 🍎 PLANO ALIMENTAR
                    | Refeição | Alimento Principal | Macronutrientes | Substituição |
                    
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
                            texto_ia = resposta.json()['candidates'][0]['content']['parts'][0]['text']
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

    if st.button("⬅️ Voltar ao Painel Inicial"):
        st.session_state.etapa = 1
        st.session_state.mensagens = []
        st.rerun()

    st.success(f"**Análise concluída, {nome}!** Confira seu protocolo abaixo.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atleta", nome)
    c2.metric("Objetivo", objetivo_curto)
    c3.metric("Peso Atual", f"{peso} kg")
    c4.metric("IMC Inicial", f"{imc:.1f}")
    
    st.divider()
    
    for msg in st.session_state.mensagens:
        if msg["role"] == "assistant":
            st.markdown(msg["content"])
        else:
            with st.chat_message("user"):
                st.markdown(msg["content"])
            
    # 🟢 NOVO: BOTÃO DE DOWNLOAD DO PDF
    st.divider()
    plano_principal = st.session_state.mensagens[0]["content"]
    
    # Gera o PDF em segundo plano
    pdf_bytes = gerar_pdf(plano_principal, nome)
    
    st.download_button(
        label="📥 Baixar Protocolo Completo em PDF",
        data=pdf_bytes,
        file_name=f"Protocolo_{nome.replace(' ', '_')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )
            
    st.divider()
    st.subheader("💬 Central de Dúvidas")
    if prompt_duvida := st.chat_input("Pergunte sobre exercícios ou substituições de alimentos..."):
        
        st.session_state.mensagens.append({"role": "user", "content": prompt_duvida})
        with st.chat_message("user"):
            st.markdown(prompt_duvida)
            
        with st.chat_message("assistant"):
            with st.spinner("Analisando protocolo..."):
                plano_contexto = st.session_state.mensagens[0]["content"]
                prompt_duvida_completo = f"Plano:\n{plano_contexto}\n\nDúvida: {prompt_duvida}"
                
                url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                payload = {"contents": [{"parts": [{"text": prompt_duvida_completo}]}]}
                
                try:
                    resposta = requests.post(url, json=payload, timeout=20)
                    if resposta.status_code == 200:
                        texto_ia_duvida = resposta.json()['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(texto_ia_duvida)
                        st.session_state.mensagens.append({"role": "assistant", "content": texto_ia_duvida})
                        
                        st.session_state.banco[usuario]["perfis"][nome]["mensagens"] = st.session_state.mensagens
                        salvar_banco(st.session_state.banco)
                    else:
                        st.warning("Servidor ocupado. Tente perguntar em alguns instantes.")
                except:
                    st.error("Erro ao conectar.")
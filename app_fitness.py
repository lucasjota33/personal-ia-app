import streamlit as st
import requests

# Configurações iniciais
CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash-lite"

# Configuração da Página
st.set_page_config(page_title="Fitness AI", page_icon="⚡", layout="wide")

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    /* Oculta botões superiores (Share, Deploy) */
    [data-testid="stToolbar"], [data-testid="stToolbarActions"], .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    header {
        background-color: transparent !important;
        box-shadow: none !important;
    }
    #MainMenu, footer { display: none !important; }
    
    /* Previne o corte no topo */
    .block-container {
        padding-top: 4rem !important; 
        margin-top: 2rem !important;
    }
    
    /* Estiliza os cards */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 10% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE ESTADO (MEMÓRIA DO APP) ---
if "etapa" not in st.session_state:
    st.session_state.etapa = 1
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = {}
if "historico" not in st.session_state:
    st.session_state.historico = {} # Aqui guardamos os perfis salvos!

# --- BARRA LATERAL (HISTÓRICO DE ALUNOS) ---
with st.sidebar:
    st.title("📋 Meus Alunos")
    st.markdown("Perfis gerados recentemente:")
    
    if not st.session_state.historico:
        st.info("Nenhum histórico salvo ainda.")
    else:
        for nome_salvo in st.session_state.historico.keys():
            # Cria um botão para cada aluno salvo
            if st.button(f"👤 {nome_salvo}", use_container_width=True):
                # Se clicar, carrega os dados e vai para a Etapa 2
                st.session_state.dados_usuario = st.session_state.historico[nome_salvo]["dados"]
                st.session_state.mensagens = st.session_state.historico[nome_salvo]["mensagens"]
                st.session_state.etapa = 2
                st.rerun()
                
    st.divider()
    if st.button("➕ Novo Atleta", type="primary", use_container_width=True):
        st.session_state.etapa = 1
        st.session_state.dados_usuario = {}
        st.session_state.mensagens = []
        st.rerun()


# ==========================================================
# ETAPA 1: PÁGINA DE COLETA DE DADOS (FORMULÁRIO)
# ==========================================================
if st.session_state.etapa == 1:
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚡ Treinador Digital")
        st.write("Preencha seus dados abaixo para gerar um protocolo de elite.")
        
        with st.form("perfil_usuario"):
            nome = st.text_input("Nome Completo", placeholder="Ex: Lucas")
            
            c_peso, c_altura = st.columns(2)
            with c_peso:
                peso = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
            with c_altura:
                altura = st.number_input("Altura (cm)", min_value=100, max_value=230, value=175, step=1)
                
            objetivo = st.selectbox("Objetivo Principal", [
                "Ganhar Massa Muscular (Hipertrofia)",
                "Perder Peso (Déficit Calórico)",
                "Melhorar Performance (Força/Resistência)",
                "Definição Corporal",
                "Manutenção da Saúde"
            ])
            
            nivel_atividade = st.selectbox("Nível de Atividade Diária", [
                "Sedentário (pouco ou nenhum exercício)",
                "Levemente Ativo (exercício leve 1-3 dias/semana)",
                "Moderadamente Ativo (exercício moderado 3-5 dias/semana)",
                "Muito Ativo (exercício pesado 6-7 dias/semana)",
                "Extremamente Ativo (trabalho físico pesado/atleta)"
            ])

            st.write("")
            submit_button = st.form_submit_button(label="🚀 GERAR PROTOCOLO ELITE", type="primary", use_container_width=True)

        if submit_button:
            if not nome:
                st.error("⚠️ Identificação necessária. Por favor, preencha seu nome.")
            # Verifica se o nome já existe para não sobrescrever sem querer (opcional)
            elif nome in st.session_state.historico:
                st.warning(f"O atleta '{nome}' já existe no histórico! Acesse pela barra lateral ou use outro nome.")
            else:
                st.session_state.dados_usuario = {
                    "nome": nome, "peso": peso, "altura": altura, 
                    "objetivo": objetivo, "nivel": nivel_atividade
                }
                
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
                            
                            # SALVA NO HISTÓRICO!
                            st.session_state.historico[nome] = {
                                "dados": st.session_state.dados_usuario,
                                "mensagens": st.session_state.mensagens
                            }
                            
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
    
    dados = st.session_state.dados_usuario
    nome = dados["nome"]
    peso = dados["peso"]
    altura = dados["altura"]
    objetivo_curto = dados["objetivo"].split("(")[0].strip()
    imc = peso / ((altura / 100) ** 2)

    st.success(f"**Análise concluída, {nome}!** Confira seu protocolo abaixo.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atleta", nome)
    c2.metric("Objetivo", objetivo_curto)
    c3.metric("Peso Atual", f"{peso} kg")
    c4.metric("IMC Inicial", f"{imc:.1f}")
    
    st.divider()
    
    # Exibe histórico do chat
    for msg in st.session_state.mensagens:
        if msg["role"] == "assistant":
            st.markdown(msg["content"])
        else:
            with st.chat_message("user"):
                st.markdown(msg["content"])
            
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
                        
                        # ATUALIZA O HISTÓRICO COM A NOVA MENSAGEM DO CHAT!
                        st.session_state.historico[nome]["mensagens"] = st.session_state.mensagens
                    else:
                        st.warning("Servidor ocupado. Tente perguntar em alguns instantes.")
                except:
                    st.error("Erro ao conectar.")
import streamlit as st
import requests

# Configurações iniciais
CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash-lite"

# Configuração da Página (DEVE ser o primeiro comando)
st.set_page_config(page_title="Fitness AI", page_icon="⚡", layout="wide")

# --- CSS CUSTOMIZADO (Design de Software Proprietário) ---
st.markdown("""
    <style>
    /* 1. Oculta TODOS os botões do canto superior direito */
    [data-testid="stToolbar"], 
    [data-testid="stToolbarActions"], 
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }

    /* 2. Deixa o fundo do cabeçalho invisível */
    header {
        background-color: transparent !important;
        box-shadow: none !important;
    }

    /* 3. Oculta o rodapé e menu padrão */
    #MainMenu, footer {
        display: none !important;
    }

    /* 4. A CORREÇÃO DO CORTE: Força a página principal a começar mais para baixo */
    .block-container {
        padding-top: 4rem !important; 
        margin-top: 2rem !important;
    }

    /* 5. Estiliza os cards de métricas */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 10% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE ESTADO (Controla em qual página estamos) ---
if "etapa" not in st.session_state:
    st.session_state.etapa = 1
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = {}

# ==========================================================
# ETAPA 1: PÁGINA DE COLETA DE DADOS (FORMULÁRIO)
# ==========================================================
if st.session_state.etapa == 1:
    
    # Centraliza o cabeçalho
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
            else:
                # Salva os dados na memória para usar na Etapa 2
                st.session_state.dados_usuario = {
                    "nome": nome, "peso": peso, "altura": altura, 
                    "objetivo": objetivo, "nivel": nivel_atividade
                }
                
                with st.spinner("⏳ Processando biometria e estruturando planejamento de alta performance..."):
                    
                    prompt_mestre = f"""
                    Atue como um Nutricionista Esportivo Clínico e Personal Trainer de Atletas de Elite. 
                    Sua missão é criar um planejamento irretocável, 100% aplicável e científico para o(a) {nome}.

                    DADOS BIOMÉTRICOS E OBJETIVO:
                    - Peso: {peso}kg | Altura: {altura}cm
                    - Nível de Atividade: {nivel_atividade}
                    - Objetivo Principal: {objetivo}

                    ESTRUTURA OBRIGATÓRIA DA SUA RESPOSTA (Siga estritamente os tópicos e use tabelas Markdown):

                    # 🏆 PROTOCOLO DE ELITE: {nome.upper()}

                    ## 1. 📊 ANÁLISE METABÓLICA
                    Elabore uma planilha detalhada com os seguintes cálculos, utilizando fórmulas validadas pela literatura científica, exiba penas as informações a seguir:
                    - **Taxa Metabólica Basal:** (Calcule estimativa usando equação de Mifflin-St Jeor).
                    - **Gasto Energético Total:** (Calcule baseado no nível de atividade).
                    - **Meta Calórica Alvo:** (Estabeleça as calorias diárias exatas para atingir o objetivo).

                    ---
                    ## 2. 🍎 PLANO ALIMENTAR SEMANAL COMPLETO (Dietética Prática)
                    Elabore uma planilha detalhada com cardápio para a dieta do usuário. Aplique variedade real aos alimentos para evitar uma dieta monótona, alternando as fontes de proteínas e carboidratos ao longo dos dias.
                    Adicione opções de substituição para cada refeição, garantindo flexibilidade e aderência.
                    Não há a necessidade de criar um cardápio para cada dia da semana, apenas um cardápio completo, para o usuário seguir durante a semana.
                    Mantenha o seguinte formato em Markdown, seguindo estritamente as colunas abaixo:
                    | Refeição | Alimento Principal (gramas) | Macronutrientes | Opção de Substituição |
                    
                    ## 3. 🏋️‍♂️ PLANILHA DE TREINAMENTO DE ALTA PERFORMANCE
                    Defina uma divisão semanal inteligente (ex:ABCDE, ABC, AB, Fullbody) com base no objetivo.
                    Para CADA DIA de treino, crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
                    | Exercício (Técnica/Equipamento) | Séries | Repetições | Descanso |
                    | :--- | :--- | :--- | :--- |
                    *(Nota: Cadência refere-se ao tempo de movimento, ex: 3010. RIR refere-se a quantas repetições devem sobrar no tanque antes da falha, ex: RIR 1-2).*
                    - Escolha exercícios com foco em biomecânica eficiente e progressão de carga. Inclua aquecimento/mobilidade no início.

                    ---
                    ## 4. 💊 SUPLEMENTAÇÃO BASEADA EM EVIDÊNCIAS
                    Liste apenas suplementos de Nível A de evidência científica (ex: Creatina, Cafeína, Whey Protein, se necessário) com dosagens ajustadas para {peso}kg e o melhor horário de consumo.
                    Crie uma tabela em Markdown seguindo EXATAMENTE as colunas abaixo:
                    | Suplemento | Dosagem Diária | Horário Ideal de Consumo |
                    """

                    url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                    payload = {"contents": [{"parts": [{"text": prompt_mestre}]}]}
                    
                    try:
                        resposta = requests.post(url, json=payload, timeout=40) 
                        
                        if resposta.status_code == 200:
                            texto_ia = resposta.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state.mensagens = [{"role": "assistant", "content": texto_ia}]
                            # Avança para a Etapa 2 e recarrega a página
                            st.session_state.etapa = 2
                            st.rerun()
                        else:
                            st.error(f"Erro no Servidor ({resposta.status_code}). Tente novamente.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

# ==========================================================
# ETAPA 2: PÁGINA DO PLANO GERADO E CHAT DA IA
# ==========================================================
elif st.session_state.etapa == 2:
    
    # Recupera os dados salvos na Etapa 1
    dados = st.session_state.dados_usuario
    nome = dados["nome"]
    peso = dados["peso"]
    altura = dados["altura"]
    objetivo_curto = dados["objetivo"].split("(")[0].strip()
    imc = peso / ((altura / 100) ** 2)

    # Botão para voltar e fazer um novo plano
    if st.button("⬅️ Voltar / Novo Aluno"):
        st.session_state.etapa = 1
        st.session_state.mensagens = []
        st.rerun()

    # Header de sucesso com dashboard de métricas
    st.success(f"**Análise concluída, {nome}!** Confira seu protocolo abaixo.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atleta", nome)
    c2.metric("Objetivo", objetivo_curto)
    c3.metric("Peso Atual", f"{peso} kg")
    c4.metric("IMC Inicial", f"{imc:.1f}")
    
    st.divider()
    
    # Exibe o plano formatado e histórico do chat
    for msg in st.session_state.mensagens:
        if msg["role"] == "assistant":
            st.markdown(msg["content"])
        else:
            with st.chat_message("user"):
                st.markdown(msg["content"])
            
    # Chat para dúvidas
    st.divider()
    st.subheader("💬 Central de Dúvidas")
    if prompt_duvida := st.chat_input("Dúvida sobre um exercício, alimento ou execução? Pergunte aqui..."):
        
        st.session_state.mensagens.append({"role": "user", "content": prompt_duvida})
        with st.chat_message("user"):
            st.markdown(prompt_duvida)
            
        with st.chat_message("assistant"):
            with st.spinner("Analisando protocolo..."):
                plano_contexto = st.session_state.mensagens[0]["content"]
                prompt_duvida_completo = f"Com base no plano gerado anteriormente:\n\n[PLANO]\n{plano_contexto}\n\n[DÚVIDA DO USUÁRIO]\n{prompt_duvida}"
                
                url = f"https://generativelanguage.googleapis.com/v1beta/{MODELO}:generateContent?key={CHAVE}"
                payload = {"contents": [{"parts": [{"text": prompt_duvida_completo}]}]}
                
                try:
                    resposta = requests.post(url, json=payload, timeout=20)
                    if resposta.status_code == 200:
                        texto_ia_duvida = resposta.json()['candidates'][0]['content']['parts'][0]['text']
                        st.markdown(texto_ia_duvida)
                        st.session_state.mensagens.append({"role": "assistant", "content": texto_ia_duvida})
                    else:
                        st.warning("Servidor ocupado. Tente perguntar em alguns instantes.")
                except:
                    st.error("Erro ao conectar.")
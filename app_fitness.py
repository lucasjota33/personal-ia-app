import streamlit as st
import requests

# Configurações iniciais
CHAVE = st.secrets["GEMINI_API_KEY"]
MODELO = "models/gemini-2.5-flash-lite"

# Configuração da Página (DEVE ser o primeiro comando)
st.set_page_config(page_title="Fitness AI", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO (Deixa o app com cara de software profissional) ---
# --- CSS CUSTOMIZADO (Deixa o app com cara de software profissional) ---
st.markdown("""
    <style>
    /* Esconde o rodapé padrão do Streamlit */
    footer {visibility: hidden;}
    
    /* Esconde as opções superiores (Share, Deploy, GitHub) */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Deixa o cabeçalho invisível mas mantém a estrutura para não quebrar o layout */
    header {
        background: transparent !important;
    }
    
    /* 👇 CORREÇÃO DO CORTE SUPERIOR: Aumentamos o padding-top de 2rem para 5rem */
    .block-container {
        padding-top: 5rem !important; 
        padding-bottom: 2rem !important;
    }
    
    /* Estiliza os cards de métricas */
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 10% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (COLETA DE DADOS) ---
with st.sidebar:
    st.title("⚡ Treinador digital")
    st.image("https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=1470&auto=format&fit=crop", use_container_width=True)
    st.markdown("Preencha seu perfil biométrico abaixo.")
    
    with st.form("perfil_usuario"):
        nome = st.text_input("Nome Completo", placeholder="Ex: Lucas")
        col1, col2 = st.columns(2)
        with col1:
            peso = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=75.0, step=0.1)
        with col2:
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

        # Botão em destaque
        st.write("")
        submit_button = st.form_submit_button(label="🚀 GERAR PROTOCOLO ELITE", type="primary", use_container_width=True)

# --- LÓGICA DE GERAÇÃO DO PLANO ---

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

if submit_button:
    if not nome:
        st.error("⚠️ Identificação necessária. Por favor, preencha seu nome na barra lateral.")
    else:
        st.session_state.mensagens = []
        
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
                    st.session_state.mensagens.append({"role": "assistant", "content": texto_ia})
                    st.toast("Protocolo gerado com sucesso!", icon="✅")
                else:
                    st.error(f"Erro no Servidor ({resposta.status_code}). Tente novamente.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- EXIBIÇÃO DA TELA PRINCIPAL ---

if not st.session_state.mensagens:
    # TELA DE APRESENTAÇÃO (Se não houver plano gerado)
    st.title("Construa sua melhor versão 🧬")
    st.write("Nosso algoritmo analisa sua biometria e objetivos para criar um protocolo de nível atlético em segundos.")
    st.write("---")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🏋️‍♂️ Treino de Elite")
        st.write("Periodização baseada em biomecânica, cadência e controle de falha (RIR).")
    with c2:
        st.subheader("🍎 Nutrição Clínica")
        st.write("Cálculos exatos de TMB, GET e macros, com cardápios e gramagens precisas.")
    with c3:
        st.subheader("🤖 Suporte Contínuo")
        st.write("Converse com a IA a qualquer momento para adaptar exercícios ou tirar dúvidas.")
        
else:
    # TELA DO PLANO GERADO
    
    # Header de sucesso com dashboard de métricas
    st.success(f"**Análise concluída, {nome}!** Confira seu protocolo abaixo.")
    
    imc = peso / ((altura / 100) ** 2)
    objetivo_curto = objetivo.split("(")[0].strip()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atleta", nome)
    c2.metric("Objetivo", objetivo_curto)
    c3.metric("Peso Atual", f"{peso} kg")
    c4.metric("IMC Inicial", f"{imc:.1f}")
    
    st.divider()
    
    # Exibe o plano formatado
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
# Usa uma versão leve do Python
FROM python:3.10-slim

# Define a pasta de trabalho dentro do servidor
WORKDIR /app

# Copia os requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do seu código para o servidor
COPY . .

# Expõe a porta que o Google Cloud Run exige (8080)
EXPOSE 8080

# 🟢 AQUI ESTÁ A MUDANÇA: Apontando para o seu script correto
CMD ["streamlit", "run", "app_fitness.py", "--server.port=8080", "--server.address=0.0.0.0"]
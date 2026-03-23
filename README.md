# 🚀 Pesquisa-AI
> Transforme dados de pesquisas em insights inteligentes com análise estatística e IA integrada.

Plataforma web completa para **criação de formulários**, **coleta de respostas** e **análise estatística com Inteligência Artificial**.

Desenvolvida com Django e PostgreSQL, a aplicação permite transformar dados brutos em **insights claros e acionáveis**.

## 🌐 Acesse o projeto
https:?

---

## 🧠 Diferencial

Diferente de sistemas tradicionais de pesquisa, o Pesquisa-AI:

- Analisa dados automaticamente  
- Gera estatísticas completas em tempo real  
- Utiliza IA (Groq + Llama 3.1) para interpretar resultados  
- Permite análise de CSV com insights em linguagem natural  

---

## 📸 Demonstração

### Dashboard
<img width="1919" height="1076" alt="image" src="https://github.com/user-attachments/assets/acfe17d1-a534-4519-9552-3e09479b4836" />


### Criação de Formulário
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/055b2ca1-fe96-4651-8239-9c3240253de2" />


### Análise com IA
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/a5037b83-8c94-4035-9f00-bb045621e8b4" />


---

## 🚀 Funcionalidades

### 📋 Formulários
- Criação de formulários personalizados  
- Perguntas:
  - Numérica  
  - Múltipla escolha  
  - Texto livre  
- Definição de pergunta principal  
- Coleta ilimitada de respostas  

---

### 📊 Dashboard Estatístico
- Média, mediana, moda  
- Desvio padrão, mínimo, máximo  
- Amplitude e total  
- Gráficos interativos (Chart.js)  
- Análise de distribuição e assimetria  
- Upload de CSV (até 20.000 linhas)  

---

### 🤖 Inteligência Artificial
- Chat com analista de dados  
- Respostas contextualizadas  
- Interpretação automática de dados  
- Análise de CSV com IA  
- Fallback sem API  

---

## 🛠️ Tecnologias

| Camada        | Tecnologia |
|--------------|-----------|
| Backend      | Django 5 |
| Banco        | PostgreSQL |
| IA           | Groq (Llama 3.1 8B) |
| Gráficos     | Chart.js |
| Frontend     | HTML, CSS, JS |
| Servidor     | Gunicorn |

---

## ⚙️ Instalação

```bash
# Clone o repositório
git clone https://github.com/Thiagoolivs/Pesquisa-AI.git

cd Pesquisa-AI

# Ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Dependências
pip install -r requirements.txt


🔐 Variáveis de Ambiente

Crie um .env:

SESSION_SECRET=sua-chave
PGHOST=localhost
PGPORT=5432
PGDATABASE=pesquisa_ai
PGUSER=postgres
PGPASSWORD=sua_senha
GROQ_API_KEY=sua_api_key
🗄️ Banco de Dados
python manage.py migrate
▶️ Execução
python manage.py runserver

Acesse:

http://localhost:8000

```

## 🧪 Como Usar
Ação	Passos
Criar pesquisa	Acesse /pesquisa
Crie perguntas
Defina uma como principal
Coletar respostas	Preencha e envie formulários
Dados são armazenados automaticamente
Analisar dados	Dashboard com estatísticas
Upload de CSV
Gráficos automáticos
Usar IA	Acesse /ia
Faça perguntas em linguagem natural
Receba insights
## 📁 Estrutura do Projeto
Pasta / Arquivo	Descrição
config/	Configurações do Django
core/	Models, views e lógica de negócio
static/	CSS, JS e arquivos estáticos
templates/	Templates HTML
manage.py	Entrypoint do Django
requirements.txt	Dependências do projeto
## 📌 Rotas principais
Método	Rota	Descrição
GET	/	Dashboard
GET	/pesquisa	Formulários
GET	/ia	IA
POST	/upload_csv	Análise CSV
POST	/formulario	Criar formulário

## 👨‍💻 Autor

Thiago de Oliveira Coelho Souza
2026

## 📄 Licença

Todos os direitos reservados.

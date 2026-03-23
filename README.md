# Pesquisa AI

Plataforma web completa para criação de formulários de pesquisa, coleta de respostas e análise estatística com inteligência artificial. Desenvolvida em Django com banco de dados PostgreSQL.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Banco de Dados](#banco-de-dados)
- [Rotas da Aplicação](#rotas-da-aplicação)
- [Como Usar](#como-usar)

---

## Visão Geral

O **Pesquisa AI** permite criar formulários personalizados, coletar respostas em tempo real e visualizar análises estatísticas completas com gráficos interativos. A integração com a API Groq (modelo Llama 3.1) adiciona uma camada de inteligência artificial capaz de interpretar os dados e gerar insights contextualizados em linguagem natural.

---

## Funcionalidades

### Formulários
- Criação de formulários com título e descrição
- Três tipos de perguntas: **Numérica**, **Múltipla Escolha** e **Texto Livre**
- Definição de pergunta principal para acompanhamento no dashboard
- Coleta ilimitada de respostas, persistidas no banco de dados

### Dashboard Estatístico
- Cálculo automático de: média, mediana, moda, desvio padrão, mínimo, máximo, amplitude e total
- Gráficos interativos de distribuição (barras, linhas e rosca) via Chart.js
- Análise de assimetria e concentração dos dados
- Upload de arquivos CSV para análise avulsa (até 10.000 valores)

### Inteligência Artificial
- Chat interativo com analista de dados por IA (Groq / Llama 3.1)
- Respostas contextualizadas com base nos dados estatísticos carregados
- Análise automática de CSV com geração de insights e tendências
- Fallback inteligente quando a API não está disponível

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Framework | Django 5.x |
| Banco de Dados | PostgreSQL |
| Servidor WSGI | Gunicorn |
| IA / LLM | Groq API (Llama 3.1 8B Instant) |
| Gráficos | Chart.js 4 (CDN) |
| Ícones | Font Awesome (CDN) |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |

---

## Pré-requisitos

- Python 3.11 ou superior
- PostgreSQL 14 ou superior
- Conta na [Groq](https://console.groq.com) para obter uma API key (opcional, mas necessário para a funcionalidade de IA)

---

## Instalação e Execução

### 1. Clone o repositório

```bash
git clone <url-do-repositório>
cd <nome-do-repositório>
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

### 3. Instale as dependências

```bash
pip install -r artifacts/pesquisa-flask/requirements.txt
```

### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz ou exporte as variáveis diretamente no terminal (veja a seção [Variáveis de Ambiente](#variáveis-de-ambiente)).

### 5. Execute as migrações do banco de dados

```bash
cd artifacts/pesquisa-flask
python manage.py migrate
```

### 6. Inicie o servidor

```bash
gunicorn --bind 0.0.0.0:5000 --reload config.wsgi:application
```

Acesse em: [http://localhost:5000](http://localhost:5000)

---

## Variáveis de Ambiente

| Variável | Obrigatório | Descrição |
|---|---|---|
| `SESSION_SECRET` | Sim | Chave secreta do Django. Use uma string longa e aleatória em produção. |
| `PGHOST` | Sim | Host do banco de dados PostgreSQL. |
| `PGPORT` | Não | Porta do PostgreSQL (padrão: `5432`). |
| `PGDATABASE` | Sim | Nome do banco de dados. |
| `PGUSER` | Sim | Usuário do banco de dados. |
| `PGPASSWORD` | Sim | Senha do banco de dados. |
| `GROQ_API_KEY` | Não | API key da Groq para habilitar análises com IA. Sem ela, a IA usa respostas baseadas em regras. |

### Exemplo de `.env`

```env
SESSION_SECRET=sua-chave-secreta-longa-e-aleatória
PGHOST=localhost
PGPORT=5432
PGDATABASE=pesquisa_ai
PGUSER=postgres
PGPASSWORD=sua-senha
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

> **Dica:** Nunca versione o arquivo `.env`. Adicione-o ao `.gitignore`.

---

## Estrutura do Projeto

```
artifacts/pesquisa-flask/
├── config/
│   ├── settings.py        # Configurações do Django
│   ├── urls.py            # Roteamento principal
│   └── wsgi.py            # Entrypoint WSGI para o Gunicorn
├── core/
│   ├── migrations/        # Migrações do banco de dados
│   ├── templatetags/      # Filtros customizados para templates
│   ├── models.py          # Models: Formulario, Pergunta, Resposta, etc.
│   ├── views.py           # Lógica de negócio e endpoints da API
│   ├── stats.py           # Funções de cálculo estatístico
│   ├── apps.py            # Configuração da app Django
│   └── urls.py            # Rotas da app core
├── static/
│   └── css/style.css      # Estilos da interface
├── templates/
│   ├── base.html          # Template base com navegação
│   ├── dashboard.html     # Página de análise e gráficos
│   ├── pesquisa.html      # Criação e resposta de formulários
│   └── ia.html            # Interface de chat com IA
├── manage.py
└── requirements.txt
```

---

## Banco de Dados

O projeto usa PostgreSQL com os seguintes models:

### `Formulario`
Armazena os formulários criados.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer (PK) | Identificador único |
| `titulo` | CharField | Título do formulário |
| `descricao` | TextField | Descrição opcional |
| `criado_em` | DateTimeField | Data e hora de criação |

### `Pergunta`
Perguntas vinculadas a um formulário.

| Campo | Tipo | Descrição |
|---|---|---|
| `formulario` | FK → Formulario | Formulário ao qual pertence |
| `pergunta_id` | CharField | ID único gerado pelo cliente |
| `texto` | TextField | Enunciado da pergunta |
| `tipo` | CharField | `numerica`, `multipla_escolha` ou `texto` |
| `principal` | BooleanField | Pergunta principal para o dashboard |
| `ordem` | IntegerField | Posição na sequência |

### `OpcaoPergunta`
Opções das perguntas de múltipla escolha.

| Campo | Tipo | Descrição |
|---|---|---|
| `pergunta` | FK → Pergunta | Pergunta à qual pertence |
| `texto` | CharField | Texto da opção |

### `RespostaFormulario`
Cada submissão de um participante.

| Campo | Tipo | Descrição |
|---|---|---|
| `formulario` | FK → Formulario | Formulário respondido |
| `submetido_em` | DateTimeField | Data e hora da submissão |

### `ItemResposta`
Resposta individual para cada pergunta dentro de uma submissão.

| Campo | Tipo | Descrição |
|---|---|---|
| `resposta` | FK → RespostaFormulario | Submissão à qual pertence |
| `pergunta_id` | CharField | ID da pergunta respondida |
| `valor` | TextField | Valor inserido pelo participante |

---

## Rotas da Aplicação

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Dashboard com estatísticas e gráficos |
| `GET` | `/pesquisa` | Página de gestão do formulário |
| `GET` | `/ia` | Interface de chat com IA |
| `POST` | `/analisar` | Analisa uma lista de números e retorna estatísticas |
| `POST` | `/upload_csv` | Processa um arquivo CSV e retorna estatísticas |
| `GET` | `/formulario` | Retorna o formulário ativo em JSON |
| `POST` | `/formulario` | Cria e salva um novo formulário |
| `POST` | `/formulario/responder` | Registra uma submissão de resposta |
| `GET` | `/formulario/dados` | Retorna dados de uma pergunta específica |
| `GET` | `/formulario/analise` | Retorna análise completa de todas as perguntas |
| `POST` | `/ia_api` | Envia uma pergunta para a IA com contexto de dados |
| `POST` | `/ia_csv` | Analisa um CSV diretamente com IA |

---

## Como Usar

### Criando uma pesquisa
1. Acesse a aba **Pesquisa** no menu superior
2. Preencha o título e a descrição
3. Adicione perguntas escolhendo o tipo (Numérica, Múltipla Escolha ou Texto)
4. Marque uma pergunta numérica como **Principal** para acompanhamento no dashboard
5. Clique em **Salvar Formulário**

### Coletando respostas
1. Na aba **Pesquisa**, acesse a seção **Responder**
2. Preencha as respostas e clique em **Enviar**
3. O formulário pode ser respondido múltiplas vezes por diferentes participantes

### Analisando dados
- Acesse o **Dashboard** para ver gráficos e métricas estatísticas em tempo real
- Use o upload de CSV para analisar dados externos
- Digite números manualmente no campo de análise rápida

### Usando a IA
1. Acesse a aba **IA**
2. Os dados estatísticos carregados são passados automaticamente como contexto
3. Faça perguntas em linguagem natural: *"O que a média indica sobre os dados?"*, *"Há outliers?"*
4. Para analisar um CSV com IA, use o botão de upload na página de IA

---

## Licença

Desenvolvedor: Thiago de Oliveira Coelho Souza
Ano: 2026
Todos os Direitos Reservados.

# CorpIA - Assistente IA Corporativa

Assistente virtual inteligente para ambientes corporativos, integrado com **SharePoint**, **Microsoft Azure AD** e **Ollama** (LLaMA 3.2).

---

## 🚀 Funcionalidades

- **Autenticação Microsoft Azure AD** - Login corporativo seguro
- **Chat com IA local** - Usa Ollama com modelo LLaMA 3.2
- **Integração SharePoint** - Acesso a documentos e arquivos da empresa
- **Histórico de conversas** - Múltiplas sessões por usuário
- **Interface web responsiva** - Funciona em qualquer navegador
- **Serviço Windows** - Inicia automaticamente e reinicia em caso de falha

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Função |
|------------|--------|
| **Python 3.12** | Backend |
| **FastAPI** | API REST |
| **Uvicorn** | Servidor ASGI |
| **Ollama** | IA local (LLaMA 3.2) |
| **Microsoft Graph API** | SharePoint |
| **MSAL** | Autenticação Azure AD |
| **IIS** | Frontend web |
| **NSSM** | Serviço Windows |

---

## 📁 Estrutura do Projeto

**Frontend (IIS)**
- index.html → Tela de login
- chat.html → Interface do chat
- web.config → Configuração IIS

**Backend (FastAPI)**
- main.py → API principal
- auth.py → Autenticação Azure AD
- engine.py → Motor da IA
- sharepoint.py → Integração SharePoint
- greetings.py → Detecta saudações

---

## ⚙️ Como Funciona

1. Usuário acessa o login via IIS
2. Clica em **"Conectar com Microsoft"**
3. É redirecionado para login Azure AD
4. Após autenticação, volta para o chat
5. Perguntas sobre documentos acionam busca no SharePoint
6. IA processa e responde usando **Ollama (LLaMA 3.2)**

---

## 🔧 Instalação

### Pré-requisitos
- Windows Server com IIS
- Python 3.12
- Ollama com modelo LLaMA 3.2
- Aplicativo registrado no Azure AD
- Certificado SSL

### Dependências
```bash
pip install fastapi uvicorn msal requests pydantic
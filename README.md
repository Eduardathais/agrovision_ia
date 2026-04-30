# AgroVision

Guia completo de instalacao, preparacao do ambiente, estrutura do projeto e execucao no terminal.  
Material didatico para aula pratica de visao computacional com Python, FastAPI e YOLO11.

## Objetivo

Preparar uma maquina do zero para executar o app AgroVision, incluindo:

- Python 3.11.15
- VS Code e extensoes
- Ambiente virtual
- Bibliotecas do projeto
- Estrutura de pastas
- YOLO11
- Comandos de execucao no terminal

## 1) Padrao adotado para a turma

Para evitar incompatibilidades entre maquinas:

- Sistema operacional sugerido: Windows 10 ou Windows 11 (64 bits)
- Python: 3.11.15 (64 bits)
- Editor: Visual Studio Code
- Extensoes: Python e Pylance (Microsoft)
- Framework web: FastAPI
- Servidor local: Uvicorn
- Visao computacional: OpenCV e Pillow
- Modelo de deteccao: YOLO11 (Ultralytics)
- Peso inicial recomendado: `yolo11n.pt`

Observacao: o peso do modelo pode ser baixado automaticamente no primeiro uso via `YOLO("yolo11n.pt")`, com internet ativa.

## 2) Downloads necessarios

- Python 3.11.15 x64
- VS Code (versao estavel)
- Extensao Python (Microsoft)
- Extensao Pylance (Microsoft)
- Git (opcional, recomendado)

## 3) Instalacao do Python

1. Baixe e instale o Python 3.11.15 x64.
2. Marque **Add Python to PATH** durante a instalacao.
3. Mantenha o `pip` habilitado.
4. Feche e abra o terminal novamente.

Validacao no terminal:

```bash
python --version
pip --version
```

Esperado: Python 3.11.15 e `pip` funcional.

## 4) VS Code e extensoes

1. Instale o VS Code.
2. Abra a aba de extensoes.
3. Instale:
   - Python (Microsoft)
   - Pylance (Microsoft)
4. Opcional: Jupyter.

No VS Code, selecione o interpretador do ambiente virtual em:  
`Python: Select Interpreter`.

## 5) Estrutura recomendada do projeto

```text
agrovision_ia/
|
|- .venv/                  # ambiente virtual Python
|- main.py                 # aplicacao FastAPI (arquivo atual)
|- requirements.txt        # lista de dependencias
|- README.md               # instrucoes do projeto
|- static/                 # arquivos estaticos
|- templates/              # paginas HTML (Jinja2)
|- uploads/                # imagens enviadas para teste
|- runs/                   # saidas do YOLO (predicoes/treinos)
|- models/                 # pesos personalizados
|- dataset_agro/
|  |- images/
|  |  |- train/
|  |  `- val/
|  |- labels/
|  |  |- train/
|  |  `- val/
|  `- data.yaml
`- .gitignore
```

## 6) Criacao do projeto no disco

### Windows (PowerShell)

```powershell
cd C:\projetos
mkdir agrovision_ia
cd agrovision_ia
code .
```

### Linux/macOS (bash)

```bash
mkdir -p ~/projetos/agrovision_ia
cd ~/projetos/agrovision_ia
code .
```

## 7) Criacao e ativacao do ambiente virtual

Criar ambiente:

```bash
python -m venv .venv
```

Ativar no Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Se bloquear scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Ativar no Linux/macOS:

```bash
source .venv/bin/activate
```

## 8) Atualizacao do pip e instalacao das bibliotecas

Com `.venv` ativo:

```bash
python -m pip install --upgrade pip
pip install fastapi uvicorn python-multipart jinja2
pip install opencv-python pillow ultralytics
```

Gerar/atualizar o `requirements.txt`:

```bash
pip freeze > requirements.txt
```

## 9) Estrutura minima para teste inicial

```text
agrovision_ia/
|- .venv/
|- main.py
|- requirements.txt
|- templates/
|  `- index.html
|- static/
`- uploads/
```

## 10) Exemplo minimo de aplicacao FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>AgroVision esta rodando com sucesso</h1>"
```

## 11) Comando para rodar no terminal

Como o projeto atual usa `main.py` com instancia `app`, execute:

```bash
python -m uvicorn main:app --reload
```

Se o arquivo se chamar `app.py`, use:

```bash
python -m uvicorn app:app --reload
```

Acesso local esperado:

- <http://127.0.0.1:8000>

## 12) Teste inicial do YOLO11

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
results = model.predict("imagem_teste.jpg", save=True)
```

No primeiro uso, o download do peso pode demorar.

## 13) Estrutura do dataset para treino

```text
dataset_agro/
|- images/
|  |- train/
|  `- val/
|- labels/
|  |- train/
|  `- val/
`- data.yaml
```

Exemplo de `data.yaml`:

```yaml
path: dataset_agro
train: images/train
val: images/val
names:
  0: boi
```

Cada imagem deve ter seu arquivo `.txt` correspondente em `labels/`.

## 14) Ordem recomendada da aula pratica

1. Instalar Python e validar no terminal
2. Instalar VS Code e extensoes
3. Criar pasta do projeto
4. Criar e ativar ambiente virtual
5. Instalar bibliotecas
6. Criar app minimo
7. Rodar Uvicorn e abrir no navegador
8. Testar YOLO11
9. Apresentar `dataset_agro` para treino futuro

## 15) Erros comuns e correcoes

- `uvicorn` nao reconhecido:
  - Causa: `.venv` inativo ou pacote nao instalado
  - Correcao: ativar `.venv` e instalar `uvicorn`
- `Could not import module "app"`:
  - Causa: pasta errada ou nome de arquivo diferente
  - Correcao: confirmar raiz do projeto e usar `main:app` ou `app:app` conforme arquivo
- Pagina abre vazia:
  - Causa: rota principal nao criada corretamente
  - Correcao: revisar `@app.get("/")`
- Erro ao ativar `.venv` no PowerShell:
  - Causa: politica de execucao
  - Correcao: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- YOLO nao carrega:
  - Causa: `ultralytics` ausente ou sem internet no primeiro uso
  - Correcao: instalar pacote e repetir com conexao

## 16) Checklist final do aluno

- [ ] Python 3.11.15 instalado e reconhecido
- [ ] VS Code com Python e Pylance
- [ ] Pasta do projeto criada
- [ ] Ambiente virtual `.venv` criado e ativo
- [ ] Bibliotecas instaladas sem erro
- [ ] Arquivo principal (`main.py` ou `app.py`) criado
- [ ] Uvicorn executado com sucesso
- [ ] Acesso validado em <http://127.0.0.1:8000>
- [ ] Teste inicial do YOLO11 realizado

---

Material preparado para uso didatico no projeto AgroVision.

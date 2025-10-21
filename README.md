# Emergency Vehicle Detection API

API back-end em Python para detecção de veículos de emergência em imagens e vídeos, desenvolvida com FastAPI e MongoDB.

## Descrição

Este projeto implementa uma camada de API RESTful para comunicação entre modelos de detecção de veículos de emergência (ambulâncias, viaturas policiais, carros de bombeiros) e sirenes acionadas, o front-end e o banco de dados. A API foi desenvolvida como parte do TCC "Utilização do Reconhecimento de Imagens para Identificação de Veículos de Emergência em Operação".

## Tecnologias Utilizadas

- **FastAPI**: Framework web moderno e de alta performance para construção de APIs
- **MongoDB**: Banco de dados NoSQL para armazenamento de dados
- **Motor**: Driver assíncrono para MongoDB
- **Pydantic**: Validação de dados e serialização
- **OpenCV**: Processamento de imagens e vídeos
- **JWT**: Autenticação baseada em tokens
- **Uvicorn**: Servidor ASGI de alta performance


## Instalação

### Pré-requisitos

- Python 3.11+
- MongoDB 4.4+
- pip

### Passos

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd emergency_vehicle_api
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Executar arquivo para criar usuário admin
```bash
pip install bcrypt==4.0.1
python create_admin.py
```

5. Inicie o MongoDB (se não estiver rodando):
```bash
mongod --dbpath /caminho/para/dados
```

## Execução

### Modo de Desenvolvimento

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


A API estará disponível em `http://localhost:8000`.

## Documentação da API

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Endpoints Principais


## Integração com Modelos de ML

O serviço de detecção (`app/services/detection_service.py`) está preparado para integrar modelos de Machine Learning treinados. Atualmente, utiliza detecções mock para demonstração.

Para integrar seus modelos:

1. Coloque os arquivos dos modelos treinados no diretório `models/`
2. Atualize os caminhos no arquivo `.env`:
   ```
   VEHICLE_MODEL_PATH=./models/vehicle_detector.pt
   SIREN_MODEL_PATH=./models/siren_detector.pt
   ```
3. Implemente o carregamento e inferência dos modelos em `detection_service.py`

## Estrutura do Banco de Dados

### Coleções

#### `users`
Armazena informações dos usuários do sistema.

#### `detections`
Registra cada evento de detecção de veículo de emergência.

#### `detection_jobs`
Armazena o estado dos trabalhos de processamento de vídeo.

#### `system_logs`
Registra eventos importantes do sistema para auditoria.

Consulte `database_schema.md` para mais detalhes sobre a estrutura.

## Testes

```bash
pytest tests/
```

## Segurança

- Senhas são armazenadas com hash bcrypt
- Autenticação baseada em JWT
- Tokens expiram após 30 minutos (configurável)
- CORS configurado (ajuste para produção)
- Validação de dados com Pydantic


## Licença

Este projeto foi desenvolvido como Trabalho de Conclusão de Curso na Universidade Paulista.

## Autores

- André Trajano - RA N769823
- Danilo Bortoletto - RA N8200G0
- Caique Azevedo Coelho Leme - RA G537FC2
- Gustavo Damaceno Soares - RA G46HJC7
- Igor Pinheiro da Silva Santos - RA F3487J6

## Contato

Para dúvidas ou sugestões, entre em contato através do repositório do projeto.


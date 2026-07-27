# Controle de Equipamentos Patrimoniais

Sistema completo de controle de equipamentos patrimoniais desenvolvido com Python, Flask, SQLite e PWA.

## Requisitos

- Python 3.8+
- pip

## Instalação

1. Extraia o arquivo ZIP
2. Acesse a pasta do projeto:
   ```bash
   cd patrimonio
   ```
3. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate   # Windows
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
5. Execute o sistema:
   ```bash
   python run.py
   ```
6. Acesse no navegador: http://localhost:5000

## Usuário Padrão

- **Usuário:** admin
- **Senha:** admin

## Funcionalidades

- Login e cadastro com senhas criptografadas
- Controle de permissões (Admin / Usuário)
- Cadastro completo de equipamentos
- Observações ilimitadas por equipamento
- Cálculo automático de tempo de uso
- Lembretes de manutenção
- Dashboard com gráficos (Chart.js)
- Filtros avançados e pesquisa
- Exportação CSV
- Modo impressão
- Histórico completo de ações
- Tema claro/escuro
- PWA (instalável no celular)
- Totalmente responsivo

## Backup e Restauração

O banco de dados SQLite está em `instance/patrimonio.db`.

**Backup:** Copie o arquivo `instance/patrimonio.db`
**Restauração:** Substitua o arquivo pelo backup

## Estrutura do Projeto

```
patrimonio/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── main.py
│   │   ├── api.py
│   │   └── admin.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── img/
│   │   └── icons/
│   └── templates/
│       └── [templates HTML]
├── instance/
│   └── patrimonio.db
├── config.py
├── run.py
├── requirements.txt
├── manifest.json
├── service-worker.js
└── README.md
```

## Licença

MIT

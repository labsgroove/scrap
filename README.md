# Scraper de Ordens de Serviço

Sistema profissional de web scraping com retentativas automáticas, validação de dados e múltiplos formatos de exportação.

## Funcionalidades

- **Robustez**: Retentativas automáticas com backoff exponencial
- **Validação**: Modelos Pydantic para garantir integridade dos dados
- **Performance**: Modo headless, otimizações de memória
- **Múltiplos formatos**: Excel, CSV, JSON, SQLite
- **CLI profissional**: Argumentos de linha de comando completos
- **Checkpoint**: Continua de onde parou
- **Logging estruturado**: Logs detalhados com níveis

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

### Modo interativo (com Edge/Chrome aberto):
```bash
python main.py
```

### Modo headless (sem interface):
```bash
python main.py --headless
```

### Continuar de onde parou:
```bash
python main.py --resume
```

### Exportar múltiplos formatos:
```bash
python main.py --format all --output-dir ./dados
```

### Com configurações personalizadas:
```bash
python main.py --start-page 5 --timeout 15 --max-retries 5 -v
```

## Opções do CLI

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--headless` | Modo sem interface | `False` |
| `--start-page N` | Começa da página N | `1` |
| `--resume` | Continua do checkpoint | `False` |
| `--output FILE` | Nome do arquivo de saída | `os_extraidas.xlsx` |
| `--format FMT` | Formato: excel/csv/json/sqlite/all | `excel` |
| `--timeout N` | Timeout em segundos | `10` |
| `--max-retries N` | Máximo de retentativas | `3` |
| `-v, --verbose` | Modo debug | `False` |
| `--log-file FILE` | Salvar logs em arquivo | - |

## Estrutura do Projeto

```
scrap/
├── main.py          # CLI e entrada principal
├── scraper.py       # Lógica de scraping com retries
├── models.py        # Modelos Pydantic e configurações
├── exporter.py      # Exportação para múltiplos formatos
└── scrap.py         # Script original (legado)
```

## Como Funciona

1. **Conexão**: Conecta ao Edge/Chrome via debugger ou cria nova instância headless
2. **Extração**: Identifica tabela e extrai dados com múltiplas estratégias de fallback
3. **Validação**: Valida cada registro com Pydantic
4. **Retentativas**: Em caso de erro, tenta novamente com backoff exponencial
5. **Exportação**: Salva nos formatos solicitados
6. **Checkpoint**: Salva última página processada

## Tratamento de Erros

O sistema possui 3 níveis de proteção:

- **Retry automático**: TimeoutException, WebDriverException (3 tentativas)
- **Stale element**: Recaptura elementos obsoletos automaticamente
- **Validação**: Descarta registros inválidos sem parar o processo

## Arquivos Gerados

- `os_extraidas.xlsx` - Dados principais (Excel)
- `os_extraidas.csv` - Dados em CSV
- `os_extraidas.json` - Dados em JSON
- `os_extraidas.db` - Banco SQLite
- `ultima_pagina.txt` - Checkpoint para resume
- `report.txt` - Relatório do processamento

## Requisitos

- Python 3.8+
- Microsoft Edge ou Google Chrome
- EdgeDriver/ChromeDriver (se não usar modo debugger)

## Licença

MIT

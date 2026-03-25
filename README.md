venv\Scripts\activate
python -m venv

### Python 3.7+

### Navegador Chrome
- Google Chrome instalado
- ChromeDriver compatível com sua versão do Chrome

### Bibliotecas Python

Instale as dependências com:
```bash
pip install selenium pandas openpyxl
```

## Instalação

1. Clone ou baixe este repositório:
```bash
git clone <URL-DO-REPOSITORIO>
cd scrap
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Baixe o ChromeDriver:
   - Verifique sua versão do Chrome: `chrome://version/`
   - Baixe o ChromeDriver correspondente de: https://chromedriver.chromium.org/
   - Adicione o ChromeDriver ao PATH do seu sistema ou coloque-o na mesma pasta do script

## Como Usar

1. **Inicie o Chrome em modo debug:**
   - Windows:
     ```bash
     chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome_debug"
     ```
   - Linux/Mac:
     ```bash
     google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debug"
     ```

2. **Navegue até a página desejada** no Chrome aberto e carregue completamente a tabela que deseja extrair.

3. **Execute o script:**
   ```bash
   python scrap.py
   ```

4. **Aguarde o prompt** e pressione ENTER quando a página estiver totalmente carregada.

5. O script irá extrair os dados e criar o arquivo `os_extraidas.xlsx` no mesmo diretório.

## Estrutura do Script

- **Conexão:** Conecta-se à sessão existente do Chrome via porta 9222
- **Extração:** Identifica todas as linhas da tabela e extrai os dados das colunas
- **Processamento:** Organiza os dados em um DataFrame pandas
- **Exportação:** Salva os dados em formato Excel

## Arquivos Gerados

- `os_extraidas.xlsx`: Planilha com os dados extraídos da tabela

## Personalização

Para adaptar o script a outras tabelas:

1. Modifique os seletores CSS na linha 18
2. Ajuste os índices das colunas nas linhas 27-33
3. Altere os nomes das colunas nas linhas 47-55

## Solução de Problemas

### ChromeDriver não encontrado
- Verifique se o ChromeDriver está no PATH
- Ou especifique o caminho no código: `driver = webdriver.Chrome(executable_path='caminho/para/chromedriver', options=options)`

### Conexão recusada
- Certifique-se de que o Chrome está rodando com a flag `--remote-debugging-port=9222`
- Verifique se a porta 9222 não está sendo usada por outro processo

### Tabela não encontrada
- Verifique se o seletor CSS `"table tr"` corresponde à estrutura da página
- Use as ferramentas de desenvolvedor do Chrome para inspecionar a tabela

## Dependências

- `selenium`: Automação do navegador
- `pandas`: Manipulação de dados
- `openpyxl`: Manipulação de arquivos Excel

## Licença

Este projeto está sob licença MIT.

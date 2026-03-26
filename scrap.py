from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re
import os
import keyboard

# Configuração do driver
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")
print("Pressione ESC para encerrar e salvar.")
time.sleep(2)

encerrar_solicitado = False

def verificar_esc():
    global encerrar_solicitado
    if keyboard.is_pressed('esc'):
        print("\n[ESC] Encerrando...")
        encerrar_solicitado = True
        return True
    return False

def extrair_texto(elemento):
    """Extrai texto limpo da célula - tenta múltiplas estratégias"""
    try:
        # Estratégia 1: texto direto
        texto = elemento.text.strip()
        
        # Estratégia 2: atributo title
        if not texto:
            title = elemento.get_attribute("title")
            if title:
                texto = title.strip()
        
        # Estratégia 3: innerHTML limpo
        if not texto:
            html = elemento.get_attribute("innerHTML")
            if html:
                # Remove tags e decodifica entidades HTML básicas
                texto = re.sub(r'<[^>]+>', ' ', html).strip()
                texto = texto.replace('&nbsp;', ' ').replace('&amp;', '&')
        
        # Estratégia 4: procura elementos filhos com texto
        if not texto:
            filhos = elemento.find_elements(By.XPATH, ".//*")
            for filho in filhos:
                txt = filho.text.strip()
                if txt:
                    texto = txt
                    break
        
        # Normaliza espaços e quebras de linha
        texto = re.sub(r'\s+', ' ', texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' '))
        return texto.strip()
    except Exception as e:
        return ""

def detectar_cabecalhos(driver, tabela):
    """Detecta os cabeçalhos da tabela dinamicamente"""
    cabecalhos = []
    try:
        # Tenta encontrar th elements primeiro
        ths = tabela.find_elements(By.TAG_NAME, "th")
        if ths:
            cabecalhos = [extrair_texto(th) for th in ths]
            # Remove cabeçalhos vazios no início/fim comuns em tabelas com checkboxes
            while cabecalhos and not cabecalhos[0]:
                cabecalhos.pop(0)
            # Filtra cabeçalhos vazios restantes
            cabecalhos = [h if h else f"Col_{i}" for i, h in enumerate(cabecalhos)]
            return cabecalhos
        
        # Se não encontrou th, tenta primeira linha como cabeçalho
        primeira_linha = tabela.find_element(By.CSS_SELECTOR, "tr")
        if primeira_linha:
            tds = primeira_linha.find_elements(By.TAG_NAME, "td")
            if tds:
                cabecalhos = [extrair_texto(td) for td in tds]
                while cabecalhos and not cabecalhos[0]:
                    cabecalhos.pop(0)
                cabecalhos = [h if h else f"Col_{i}" for i, h in enumerate(cabecalhos)]
                return cabecalhos
    except Exception as e:
        print(f"Erro ao detectar cabeçalhos: {e}")
    
    # Fallback: retorna colunas genéricas
    return []

def extrair_dados_linha(linha):
    """Extrai todos os dados de uma linha da tabela"""
    try:
        colunas = linha.find_elements(By.TAG_NAME, "td")
        if not colunas:
            return []
        dados = [extrair_texto(col) for col in colunas]
        return dados
    except:
        return []

def salvar(dados, colunas, pagina, arquivo="os_extraidas.xlsx"):
    if not dados:
        return
    try:
        df = pd.DataFrame(dados, columns=colunas)
        df.to_excel(arquivo, index=False)
        with open("ultima_pagina.txt", "w") as f:
            f.write(str(pagina))
        print(f"Salvo: {len(dados)} registros, {len(colunas)} colunas (página {pagina})")
    except Exception as e:
        print(f"Erro ao salvar: {e}")

def detectar_pagina(driver):
    """Detecta número da página atual - múltiplas estratégias"""
    try:
        # Estratégia 1: XPath por classes comuns
        padroes = [
            "//span[contains(@class, 'pagina')]",
            "//div[contains(@class, 'paginacao')]",
            "//div[contains(@class, 'pagination')]",
            "//a[contains(@class, 'linklist')]",
            "//span[contains(@class, 'page')]",
            "//td[contains(text(), 'Página')]",
            "//td[contains(text(), 'Pagina')]"
        ]
        for xpath in padroes:
            try:
                elems = driver.find_elements(By.XPATH, xpath)
                for elem in elems:
                    texto = elem.text
                    # Padrões: X/Y, X de Y, Página X/Y
                    match = re.search(r'[Pp][áa]gina\s*(\d+)\s*/\s*(\d+)', texto)
                    if not match:
                        match = re.search(r'(\d+)\s*/\s*(\d+)', texto)
                    if not match:
                        match = re.search(r'(\d+)\s+de\s+(\d+)', texto, re.IGNORECASE)
                    if match:
                        return int(match.group(1)), int(match.group(2))
            except:
                continue
        
        # Estratégia 2: Busca por texto contendo números de página
        try:
            page_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '/')]")
            for elem in page_elements:
                texto = elem.text
                if 'pagina' in texto.lower() or 'página' in texto.lower():
                    match = re.search(r'(\d+)\s*/\s*(\d+)', texto)
                    if match:
                        return int(match.group(1)), int(match.group(2))
        except:
            pass
            
    except:
        pass
    return None, None

# Carrega dados existentes se houver
dados = []
cabecalhos = []
pagina_atual = 1

if os.path.exists("os_extraidas.xlsx"):
    try:
        df = pd.read_excel("os_extraidas.xlsx")
        cabecalhos = df.columns.tolist()
        dados = df.values.tolist()
        print(f"Carregados {len(dados)} registros existentes.")
        print(f"Colunas detectadas: {cabecalhos}")
        if os.path.exists("ultima_pagina.txt"):
            with open("ultima_pagina.txt", "r") as f:
                pagina_atual = int(f.read().strip()) + 1
            print(f"Continuando da página {pagina_atual}")
    except Exception as e:
        print(f"Erro ao carregar: {e}")

# Loop principal
while True:
    if verificar_esc():
        break

    print(f"\nProcessando página {pagina_atual}...")

    try:
        # Aguarda tabela carregar
        wait = WebDriverWait(driver, 10)
        tabela = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))

        # Detecta cabeçalhos dinamicamente (apenas na primeira página ou se ainda não definidos)
        if not cabecalhos or pagina_atual == 1:
            cabecalhos = detectar_cabecalhos(driver, tabela)
            if cabecalhos:
                print(f"Cabeçalhos detectados: {cabecalhos}")
            else:
                # Fallback para nomes genéricos se não conseguir detectar
                # Vai detectar na primeira linha de dados
                pass

        # Pega todas as linhas de dados (pulando cabeçalho)
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
        
        # Identifica onde começam os dados (pula th ou primeira linha de cabeçalho)
        linhas_dados = []
        for linha in linhas:
            tds = linha.find_elements(By.TAG_NAME, "td")
            if len(tds) > 0:
                linhas_dados.append(linha)
        
        print(f"Encontradas {len(linhas_dados)} linhas de dados")

        registros = 0
        for linha in linhas_dados:
            if verificar_esc():
                break

            valores = extrair_dados_linha(linha)
            
            # Se ainda não temos cabeçalhos, usa nomes genéricos baseados na primeira linha
            if not cabecalhos and valores:
                cabecalhos = [f"Col_{i}" for i in range(len(valores))]
                print(f"Cabeçalhos genéricos criados: {len(cabecalhos)} colunas")
            
            # Verifica se a linha tem dados válidos (não está vazia)
            if valores and any(v for v in valores if v.strip()):
                # Garante que temos o número correto de colunas
                if len(valores) == len(cabecalhos):
                    dados.append(valores)
                    registros += 1
                elif len(valores) > 0:
                    # Ajusta para cabeçalhos existentes (preenche ou trunca)
                    valores_ajustados = valores[:len(cabecalhos)] if len(valores) > len(cabecalhos) else valores + [""] * (len(cabecalhos) - len(valores))
                    dados.append(valores_ajustados)
                    registros += 1
                    
                # Debug: mostra primeiro registro detalhado
                if registros == 1:
                    amostra = ", ".join([f"{cabecalhos[i]}={valores[i][:20] if i < len(valores) else 'N/A'}" for i in range(min(3, len(cabecalhos)))])
                    print(f"  Exemplo: {amostra}")

        print(f"Extraídos {registros} registros")
        if cabecalhos:
            salvar(dados, cabecalhos, pagina_atual)

        if encerrar_solicitado:
            break

        # Detecta paginação
        pagina_detectada, total_paginas = detectar_pagina(driver)

        if pagina_detectada and total_paginas:
            print(f"Página {pagina_detectada}/{total_paginas}")
            if pagina_detectada >= total_paginas:
                print("Última página alcançada.")
                break

        # Aguarda avanço manual
        print("Aguardando avanço manual (ou ESC para sair)...")
        pagina_anterior = pagina_atual
        tentativas = 0

        while True:
            if verificar_esc():
                break

            time.sleep(1)
            tentativas += 1

            # Tenta detectar mudança de página
            nova_pagina, _ = detectar_pagina(driver)
            if nova_pagina and nova_pagina != pagina_anterior:
                pagina_atual = nova_pagina
                print(f"Página avançada para {pagina_atual}")
                break

            # Mostra status a cada 10s
            if tentativas % 10 == 0:
                print(f"  Aguardando... ({tentativas}s)")

        if encerrar_solicitado:
            break

    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(3)
        continue

# Salvamento final (único arquivo)
print(f"\n{'='*50}")
print(f"Total de registros extraídos: {len(dados)}")
if cabecalhos:
    print(f"Colunas: {', '.join(cabecalhos)}")
    salvar(dados, cabecalhos, pagina_atual, "os_extraidas.xlsx")
else:
    print("Nenhuma coluna detectada - nada para salvar")
print("Processo finalizado.")

driver.quit()

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
import pyautogui

# Configuração do driver
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")
print("Pressione ESC para encerrar e salvar.")
time.sleep(2)

encerrar_solicitado = False

def scroll_ate_o_fim(driver):
    """Rola a tela até o fim da página gradualmente"""
    try:
        altura_total = driver.execute_script("return document.body.scrollHeight")
        altura_atual = 0
        passo = 500
        
        while altura_atual < altura_total:
            if verificar_esc():
                break
            altura_atual += passo
            driver.execute_script(f"window.scrollTo(0, {altura_atual});")
            time.sleep(0.3)
            
            # Atualiza altura total caso a página tenha carregado mais conteúdo
            nova_altura = driver.execute_script("return document.body.scrollHeight")
            if nova_altura > altura_total:
                altura_total = nova_altura
                
        # Scroll final para garantir que chegou ao fim
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
    except Exception as e:
        print(f"Erro ao rolar página: {e}")

def clicar_proxima_pagina():
    """Clica na posição atual do mouse para avançar a página"""
    try:
        # Pega a posição atual do mouse
        x, y = pyautogui.position()
        print(f"Clicando na posição do mouse: ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Erro ao clicar: {e}")
        return False

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

def salvar(dados, pagina, arquivo="os_extraidas.xlsx"):
    if not dados:
        return
    try:
        df = pd.DataFrame(dados, columns=["OS", "Cliente", "Vendedor", "Data Abertura", "Status", "Equipamento", "OBS"])
        df.to_excel(arquivo, index=False)
        with open("ultima_pagina.txt", "w") as f:
            f.write(str(pagina))
        print(f"Salvo: {len(dados)} registros (página {pagina})")
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
pagina_atual = 1

if os.path.exists("os_extraidas.xlsx"):
    try:
        df = pd.read_excel("os_extraidas.xlsx")
        dados = df.values.tolist()
        print(f"Carregados {len(dados)} registros existentes.")
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

        # Pega todas as linhas (pulando cabeçalho)
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
        print(f"Encontradas {len(linhas)-1} linhas de dados")

        registros = 0
        for linha in linhas[1:]:  # Pula cabeçalho
            if verificar_esc():
                break

            colunas = linha.find_elements(By.TAG_NAME, "td")
            num_cols = len(colunas)
            
            # Debug: mostra todas as colunas da primeira linha
            if registros == 0 and num_cols > 0:
                print(f"  Total de colunas detectadas: {num_cols}")
                for i, col in enumerate(colunas[:10]):  # Mostra até 10 colunas
                    texto = extrair_texto(col)
                    print(f"    [{i}]: {texto[:40]}")
            
            if num_cols >= 6:
                try:
                    # Extrai dados conforme estrutura: N° OS, Cliente, Vendedor, Data abertura, Status, Equipamento, OBS
                    os_num = extrair_texto(colunas[1]) if num_cols > 1 else ""
                    cliente = extrair_texto(colunas[2]) if num_cols > 2 else ""
                    vendedor = extrair_texto(colunas[3]) if num_cols > 3 else ""
                    data_abertura = extrair_texto(colunas[4]) if num_cols > 4 else ""
                    status = extrair_texto(colunas[5]) if num_cols > 5 else ""
                    
                    # Equipamento e OBS nos índices corretos
                    equipamento = extrair_texto(colunas[6]) if num_cols > 6 else ""
                    obs = extrair_texto(colunas[7]) if num_cols > 7 else ""

                    if os_num and os_num.isdigit():
                        dados.append([os_num, cliente, vendedor, data_abertura, status, equipamento, obs])
                        registros += 1
                        
                        # Debug: mostra primeiro registro detalhado
                        if registros == 1:
                            print(f"  Exemplo extraído:")
                            print(f"    OS={os_num}")
                            print(f"    Cliente={cliente[:30]}")
                            print(f"    Vendedor={vendedor[:20]}")
                            print(f"    Data={data_abertura}")
                            print(f"    Status={status}")
                            print(f"    Equip={equipamento[:30]}")
                            print(f"    OBS={obs[:30]}")
                except Exception as e:
                    continue

        print(f"Extraídos {registros} registros")
        
        # Rola até o fim da página para processar todo o conteúdo
        print("Rolando até o fim da página...")
        scroll_ate_o_fim(driver)
        
        salvar(dados, pagina_atual)

        if encerrar_solicitado:
            break

        # Detecta paginação
        pagina_detectada, total_paginas = detectar_pagina(driver)

        if pagina_detectada and total_paginas:
            print(f"Página {pagina_detectada}/{total_paginas}")
            if pagina_detectada >= total_paginas:
                print("Última página alcançada.")
                break

        # Clica na posição do mouse para avançar para a próxima página
        print("Clique no botão 'Próxima página' e deixe o mouse parado sobre ele...")
        print("Aguardando 1 segundos...")
        time.sleep(1)
        clicar_proxima_pagina()
        
        # Aguarda avanço da página
        print("Aguardando carregamento da próxima página...")
        pagina_anterior = pagina_atual
        tentativas = 0
        max_tentativas = 15  # Timeout de 15 segundos
        pagina_mudou = False

        while tentativas < max_tentativas:
            if verificar_esc():
                break

            time.sleep(1)
            tentativas += 1

            # Tenta detectar mudança de página
            nova_pagina, _ = detectar_pagina(driver)
            if nova_pagina and nova_pagina != pagina_anterior:
                pagina_atual = nova_pagina
                print(f"Página avançada para {pagina_atual}")
                pagina_mudou = True
                break

            # Mostra status a cada 5s
            if tentativas % 5 == 0:
                print(f"  Aguardando... ({tentativas}s)")

        if not pagina_mudou:
            print("AVISO: Página não mudou. Tentando clicar novamente...")
            # Tenta clicar mais uma vez
            clicar_proxima_pagina()
            time.sleep(2)
            
            # Verifica novamente
            nova_pagina, _ = detectar_pagina(driver)
            if nova_pagina and nova_pagina != pagina_anterior:
                pagina_atual = nova_pagina
                print(f"Página avançada para {pagina_atual} (2ª tentativa)")
            else:
                print("ERRO: Não foi possível avançar para a próxima página.")
                print("Verifique se o mouse está posicionado corretamente sobre o botão.")
                break

        if encerrar_solicitado:
            break

    except Exception as e:
        print(f"Erro: {e}")
        time.sleep(3)
        continue

# Salvamento final (único arquivo)
print(f"\n{'='*50}")
print(f"Total de registros extraídos: {len(dados)}")
salvar(dados, pagina_atual, "os_extraidas.xlsx")
print("Processo finalizado.")

driver.quit()

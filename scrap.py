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
import threading
import sys

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")
print("Pressione ESC a qualquer momento para encerrar e salvar.")

time.sleep(3)

# Flag global para controle de encerramento
encerrar_solicitado = False

def verificar_tecla_esc():
    """Verifica se ESC foi pressionado para encerrar"""
    global encerrar_solicitado
    if keyboard.is_pressed('esc'):
        print("\n[ESC DETECTADO] Encerrando e salvando...")
        encerrar_solicitado = True
        return True
    return False

def aguardar_avanco_manual(driver, pagina_atual):
    """
    Aguarda o usuario avancar manualmente a pagina.
    Detecta quando a pagina mudou comparando o numero da pagina atual.
    Retorna True quando detectar que a pagina avancou.
    """
    print(f"\n{'='*60}")
    print(f"AGUARDANDO AVANCO MANUAL PARA PAGINA {pagina_atual + 1}")
    print(f"Pagina atual: {pagina_atual}")
    print("- Avance manualmente a pagina no navegador")
    print("- Ou pressione ESC para encerrar e salvar")
    print(f"{'='*60}\n")
    
    tentativas = 0
    
    while True:
        # Verifica se ESC foi pressionado
        if verificar_tecla_esc():
            return False
        
        # Verifica se a pagina mudou - tenta multiplos padroes
        page_number = detectar_numero_pagina(driver, pagina_atual)
        
        if page_number and page_number != pagina_atual:
            print(f"[DETECTOR] Pagina mudou de {pagina_atual} para {page_number}")
            return True
        
        # Aguarda antes de verificar novamente
        time.sleep(1)
        tentativas += 1
        
        # Mostra mensagem de status a cada 10 segundos
        if tentativas % 10 == 0:
            print(f"[AGUARDANDO] {tentativas}s - Ainda na pagina {pagina_atual}")

def detectar_numero_pagina(driver, pagina_esperada):
    """
    Tenta detectar o numero da pagina atual usando varias estrategias.
    Retorna o numero da pagina ou None se nao encontrar.
    """
    # Padroes de busca para texto de paginacao (case-insensitive)
    padroes_texto = [
        "pagina (",
        "pagina(", 
        "página (",
        "página(",
        "page (",
        "page(",
        "pag (",
        "pag("
    ]
    
    # Tenta encontrar elemento com algum dos padroes
    for padrao in padroes_texto:
        try:
            # Usa contains com translate para case-insensitive
            xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜ', 'abcdefghijklmnopqrstuvwxyzaaaaaaeeeeiiiiooooouuuu'), '{padrao}')]"
            elementos = driver.find_elements(By.XPATH, xpath)
            
            for elem in elementos:
                texto = elem.text.strip()
                # Procura por padrao (X/Y) ou X de Y
                match = re.search(r'[\(\s]?(\d+)[/\s](\d+)[\)\s]?', texto)
                if match:
                    return int(match.group(1))
        except:
            continue
    
    # Tenta buscar por elementos comuns de paginacao (classes, etc)
    try:
        # Procura por elementos que podem conter info de pagina
        elementos_paginacao = driver.find_elements(By.CLASS_NAME, "pagination")
        if not elementos_paginacao:
            elementos_paginacao = driver.find_elements(By.CLASS_NAME, "paginacao")
        if not elementos_paginacao:
            elementos_paginacao = driver.find_elements(By.CLASS_NAME, "page-info")
            
        for elem in elementos_paginacao:
            texto = elem.text.strip()
            match = re.search(r'(\d+)\s*[/de]\s*(\d+)', texto, re.IGNORECASE)
            if match:
                return int(match.group(1))
    except:
        pass
    
    return None

def extrair_texto_celula(elemento):
    """
    Extrai texto de uma celula da tabela.
    Garante que strings grandes sejam capturadas completamente.
    """
    try:
        # Tenta pegar o texto direto
        texto = elemento.text.strip()
        
        # Se o texto estiver vazio ou muito curto, tenta outros metodos
        if len(texto) < 10:
            # Tenta pegar o conteudo do atributo title (tooltip)
            title = elemento.get_attribute("title")
            if title:
                texto = title.strip()
        
        # Se ainda estiver vazio, tenta pegar o innerHTML sem tags
        if not texto:
            html = elemento.get_attribute("innerHTML")
            if html:
                # Remove tags HTML
                texto = re.sub(r'<[^>]+>', ' ', html).strip()
        
        # Substitui quebras de linha por espacos para manter em uma linha
        texto = texto.replace('\n', ' ').replace('\r', ' ')
        
        # Remove espacos multiplos
        texto = re.sub(r'\s+', ' ', texto)
        
        return texto
    except Exception as e:
        return ""

def inspecionar_paginacao(driver):
    """Inspecciona todos os elementos que podem ser paginação"""
    print("=== INSPECIONANDO PAGINAÇÃO ===")
    
    # Pega todos os links da página
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"Total de links encontrados: {len(all_links)}")
    
    pagination_candidates = []
    for link in all_links:
        try:
            text = link.text.strip()
            href = link.get_attribute("href") or ""
            onclick = link.get_attribute("onclick") or ""
            class_attr = link.get_attribute("class") or ""
            
            # Verifica se é candidato a paginação
            is_pagination = any([
                any(char in text for char in ['»', '›', '>', '←', '→', '‹', '«']),
                any(word in text.lower() for word in ['próxima', 'proxima', 'next', 'anterior', 'prev', 'previous']),
                text.isdigit() and int(text) > 1,
                'page' in href.lower() or 'pagina' in href.lower(),
                'page' in onclick.lower() or 'pagina' in onclick.lower(),
                'pag' in class_attr.lower() or 'page' in class_attr.lower()
            ])
            
            if is_pagination and text:
                pagination_candidates.append({
                    'text': text,
                    'href': href,
                    'onclick': onclick,
                    'class': class_attr,
                    'displayed': link.is_displayed(),
                    'enabled': link.is_enabled()
                })
        except:
            continue
    
    print(f"Candidatos a paginação encontrados: {len(pagination_candidates)}")
    for i, candidate in enumerate(pagination_candidates[:10]):  # Mostra só os 10 primeiros
        print(f"  {i+1}. Texto: '{candidate['text']}' | Class: '{candidate['class']}' | Displayed: {candidate['displayed']} | Enabled: {candidate['enabled']}")
    
    return pagination_candidates

def salvar_dados(dados, pagina_atual, nome_arquivo="os_extraidas.xlsx"):
    """Salva os dados coletados em um arquivo Excel"""
    if not dados:
        print("Nenhum dado para salvar.")
        return
    
    try:
        df = pd.DataFrame(dados, columns=[
            "OS", "Cliente", "Vendedor", "Data Abertura", "Defeito", "Equipamento", "OBS"
        ])
        df.to_excel(nome_arquivo, index=False)
        with open("ultima_pagina.txt", "w") as f:
            f.write(str(pagina_atual))
        print(f"\nDados salvos em '{nome_arquivo}' ({len(dados)} registros)")
        print(f"Ultima pagina salva: {pagina_atual}")
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")

def tentar_navegacao_por_classe(driver, target_text):
    """Tenta navegar procurando pela classe linklist"""
    try:
        # Procura especificamente pelos elementos com classe linklist
        elements = driver.find_elements(By.CLASS_NAME, "linklist")
        
        for element in elements:
            try:
                text = element.text.strip()
                if text == target_text and element.is_displayed() and element.is_enabled():
                    print(f"Clicando em '{target_text}' com classe linklist")
                    element.click()
                    return True
            except:
                continue
                
        # Tenta JavaScript nos elementos linklist
        for element in elements:
            try:
                text = element.text.strip()
                if text == target_text:
                    print(f"Clicando em '{target_text}' com JavaScript (linklist)")
                    driver.execute_script("arguments[0].click();", element)
                    return True
            except:
                continue
        
    except Exception as e:
        print(f"Erro ao tentar navegação por classe: {e}")
    
    return False

dados = []
pagina_atual = 1

# Verifica se existe arquivo parcial para continuar
if os.path.exists("os_extraidas.xlsx"):
    try:
        df_existente = pd.read_excel("os_extraidas.xlsx")
        dados = df_existente.values.tolist()
        print(f"Carregados {len(dados)} registros do arquivo existente.")
        
        # Tenta determinar a última página processada
        if os.path.exists("ultima_pagina.txt"):
            with open("ultima_pagina.txt", "r") as f:
                pagina_atual = int(f.read()) + 1
            print(f"Continuando da página {pagina_atual}...")
    except Exception as e:
        print(f"Erro ao carregar arquivo existente: {e}")
        print("Iniciando do início...")

# Se for a primeira execução, inspeciona a paginação
if pagina_atual == 1:
    inspecionar_paginacao(driver)
    print("\n" + "="*50 + "\n")
else:
    # Nas outras páginas, só verifica se há elementos linklist
    try:
        linklist_elements = driver.find_elements(By.CLASS_NAME, "linklist")
        print(f"Encontrados {len(linklist_elements)} elementos com classe 'linklist'")
    except:
        pass

while True:
    # Verifica se ESC foi pressionado no inicio de cada pagina
    if verificar_tecla_esc():
        break
    
    print(f"Processando página {pagina_atual}...")
    
    # Espera a tabela carregar completamente
    try:
        wait = WebDriverWait(driver, 15)
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        print("Tabela encontrada e carregada")
    except Exception as e:
        print(f"Erro ao esperar tabela: {e}")
        print("Tentando recarregar a página...")
        driver.refresh()
        time.sleep(5)
        continue
    
    # Pega todas as linhas da tabela
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    print(f"Encontradas {len(rows)} linhas na tabela")
    
    registros_pagina = 0
    for i in range(1, len(rows)):  # Comeca de 1 para pular o cabecalho
        # Verifica ESC a cada linha processada
        if verificar_tecla_esc():
            break
            
        row = rows[i]
        cols = row.find_elements(By.TAG_NAME, "td")
        
        if len(cols) >= 5:
            try:
                # Extrai dados usando a funcao melhorada para strings grandes
                numero_os = extrair_texto_celula(cols[1])
                cliente = extrair_texto_celula(cols[2])
                vendedor = extrair_texto_celula(cols[3]) if len(cols) > 3 else ""
                data_abertura = extrair_texto_celula(cols[4]) if len(cols) > 4 else ""
                defeito = extrair_texto_celula(cols[5]) if len(cols) > 5 else ""
                equipamento = extrair_texto_celula(cols[6]) if len(cols) > 6 else ""
                obs = extrair_texto_celula(cols[7]) if len(cols) > 7 else ""

                if numero_os:  # So adiciona se tiver numero da OS
                    dados.append([
                        numero_os,
                        cliente,
                        vendedor,
                        data_abertura,
                        defeito,
                        equipamento,
                        obs
                    ])
                    registros_pagina += 1
            except Exception as e:
                print(f"Erro ao processar linha {i}: {e}")
                continue
    
    # Verifica se ESC foi pressionado durante o processamento
    if encerrar_solicitado:
        break
    
    print(f"Extraidos {registros_pagina} registros da pagina {pagina_atual}")
    
    # Salva o progresso apos cada pagina processada
    salvar_dados(dados, pagina_atual, "os_extraidas.xlsx")
    
    # Detecta numero da pagina atual
    current_page = detectar_numero_pagina(driver, pagina_atual)
    
    if current_page:
        print(f"Pagina atual detectada: {current_page}")
        
        # Verifica se e a ultima pagina (tenta detectar total)
        try:
            page_info = driver.find_element(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜ', 'abcdefghijklmnopqrstuvwxyzaaaaaaeeeeiiiiooooouuuu'), 'pagina')] | //*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜ', 'abcdefghijklmnopqrstuvwxyzaaaaaaeeeeiiiiooooouuuu'), 'page')]")
            texto = page_info.text
            match = re.search(r'(\d+)\s*[/de]\s*(\d+)', texto, re.IGNORECASE)
            if match:
                total_pages = int(match.group(2))
                print(f"Progresso: {current_page}/{total_pages}")
                if current_page >= total_pages:
                    print("Ultima pagina alcancada. Finalizando.")
                    break
        except:
            pass
        
        # Aguarda avanco manual da pagina
        if not aguardar_avanco_manual(driver, current_page):
            break
        
        pagina_atual = current_page
    else:
        print("Nao foi possivel detectar numero da pagina. Aguardando avanco manual...")
        if not aguardar_avanco_manual(driver, pagina_atual):
            break
        pagina_atual += 1

# Salva os dados finais ao encerrar (seja por ESC ou conclusao)
if encerrar_solicitado:
    print("\nEncerramento solicitado via ESC. Salvando dados...")
    salvar_dados(dados, pagina_atual, "os_extraidas_esc.xlsx")
else:
    print("\nColeta concluida. Salvando dados finais...")
    salvar_dados(dados, pagina_atual, "os_extraidas.xlsx")

print(f"\nTotal de registros extraidos: {len(dados)}")
print("Processo finalizado.")

driver.quit()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re
import os

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")

time.sleep(3)

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
    
    # pega todas as linhas da tabela
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    print(f"Encontradas {len(rows)} linhas na tabela")
    
    registros_pagina = 0
    for i in range(1, len(rows)):  # Começa de 1 para pular o cabeçalho
        row = rows[i]
        cols = row.find_elements(By.TAG_NAME, "td")
        
        if len(cols) >= 5:
            try:
                # Extrai o número da OS (primeira coluna após o ícone)
                numero_os = cols[1].text.strip()
                cliente = cols[2].text.strip()
                vendedor = cols[3].text.strip() if len(cols) > 3 else ""
                data_abertura = cols[4].text.strip() if len(cols) > 4 else ""
                defeito = cols[5].text.strip() if len(cols) > 5 else ""
                equipamento = cols[6].text.strip() if len(cols) > 6 else ""
                obs = cols[7].text.strip() if len(cols) > 7 else ""

                if numero_os:  # Só adiciona se tiver número da OS
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
    
    print(f"Extraídos {registros_pagina} registros da página {pagina_atual}")
    
    # Verifica se existe botão de próxima página
    try:
        # Procura pelo texto "Página (X/Y)" para saber o total de páginas
        page_info = driver.find_element(By.XPATH, "//*[contains(text(), 'Página (')]")
        page_text = page_info.text
        
        # Extrai o número total de páginas usando regex
        match = re.search(r'Página \(\d+/(\d+)\)', page_text)
        if match:
            total_pages = int(match.group(1))
            print(f"Página atual: {pagina_atual}/{total_pages}")
            
            if pagina_atual >= total_pages:
                print("Última página alcançada. Finalizando.")
                break
        
        # Tenta navegação direta (sem inspecionar toda a página)
        navegacao_sucesso = False
        
        # Tenta diferentes estratégias
        strategies = [
            # 1. Procura pelo número da próxima página (prioridade)
            lambda: tentar_navegacao_por_classe(driver, str(pagina_atual + 1)),
            
            # 2. Procura por setas se não houver número
            lambda: tentar_navegacao_por_classe(driver, '»'),
            lambda: tentar_navegacao_por_classe(driver, '›'),
            lambda: tentar_navegacao_por_classe(driver, '>'),
            lambda: tentar_navegacao_por_classe(driver, '→'),
        ]
        
        for strategy in strategies:
            if strategy():
                time.sleep(3)
                navegacao_sucesso = True
                break
        
        if navegacao_sucesso:
            # Espera a página carregar completamente
            time.sleep(3)
            
            # Tenta várias vezes verificar se mudou de página
            pagina_mudou = False
            for tentativa in range(3):
                try:
                    new_page_info = driver.find_element(By.XPATH, "//*[contains(text(), 'Página (')]")
                    new_page_text = new_page_info.text
                    new_match = re.search(r'Página \((\d+)/(\d+)\)', new_page_text)
                    if new_match:
                        current_page = int(new_match.group(1))
                        print(f"Verificação {tentativa + 1}: página atual é {current_page}")
                        if current_page > pagina_atual:
                            print(f"Sucesso! Avançou para página {current_page}")
                            pagina_mudou = True
                            break
                        elif tentativa < 2:
                            print(f"Aguardando mais um pouco... (tentativa {tentativa + 1}/3)")
                            time.sleep(2)
                except:
                    if tentativa < 2:
                        time.sleep(2)
                        continue
            
            if not pagina_mudou:
                print("ERRO: Página não avançou após várias tentativas! Tentando novamente...")
                continue
            
            # Salva o progresso a cada 5 páginas
            if pagina_atual % 5 == 0:
                df_progresso = pd.DataFrame(dados, columns=[
                    "OS", "Cliente", "Vendedor", "Data Abertura", "Defeito", "Equipamento", "OBS"
                ])
                df_progresso.to_excel("os_extraidas.xlsx", index=False)
                with open("ultima_pagina.txt", "w") as f:
                    f.write(str(pagina_atual))
                print(f"Progresso salvo: página {pagina_atual}")
            
            pagina_atual += 1
        else:
            print("Não foi possível encontrar botão de navegação. Finalizando...")
            # Tenta salvar os dados atuais antes de finalizar
            if dados:
                df_final = pd.DataFrame(dados, columns=[
                    "OS", "Cliente", "Vendedor", "Data Abertura", "Defeito", "Equipamento", "OBS"
                ])
                df_final.to_excel("os_extraidas_final.xlsx", index=False)
                print("Dados finais salvos em 'os_extraidas_final.xlsx'")
            break
            
    except Exception as e:
        print(f"Erro na navegação (página {pagina_atual}): {e}")
        print("Tentando continuar...")
        
        # Tenta salvar dados coletados até agora
        if dados:
            df_parcial = pd.DataFrame(dados, columns=[
                "OS", "Cliente", "Vendedor", "Data Abertura", "Defeito", "Equipamento", "OBS"
            ])
            df_parcial.to_excel(f"os_parcial_pagina_{pagina_atual}.xlsx", index=False)
            print(f"Dados parciais salvos em 'os_parcial_pagina_{pagina_atual}.xlsx'")
        
        # Tenta recarregar a página e continuar
        try:
            driver.refresh()
            time.sleep(3)
            continue
        except:
            print("Não foi possível recuperar. Finalizando.")
            break

df = pd.DataFrame(dados, columns=[
    "OS",
    "Cliente",
    "Vendedor",
    "Data Abertura",
    "Defeito",
    "Equipamento",
    "OBS"
])

print(f"\nTotal de registros extraídos: {len(df)}")
print(df)

df.to_excel("os_extraidas.xlsx", index=False)
print(f"\nDados salvos em 'os_extraidas.xlsx'")

driver.quit()

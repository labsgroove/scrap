from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")

time.sleep(3)

dados = []
pagina_atual = 1

# Verifica se existe arquivo parcial para continuar
import os
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

while True:
    print(f"Processando página {pagina_atual}...")
    
    # pega todas as linhas da tabela
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    
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

                dados.append([
                    numero_os,
                    cliente,
                    vendedor,
                    data_abertura,
                    defeito,
                    equipamento,
                    obs
                ])
            except Exception as e:
                print(f"Erro ao processar linha {i}: {e}")
                continue
    
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
        
        # Tenta clicar no botão de próxima página - várias tentativas
        next_button = None
        selectors = [
            "//a[contains(text(), '»')]",
            "//a[contains(text(), 'Próxima')]", 
            "//a[contains(text(), 'Next')]",
            "//a[contains(@class, 'next')]",
            "//a[contains(@class, 'proxima')]",
            "//li[contains(@class, 'next')]/a",
            "//span[contains(text(), '»')]/parent::a",
            "//button[contains(text(), '»')]",
            "//button[contains(text(), 'Próxima')]"
        ]
        
        for selector in selectors:
            try:
                wait = WebDriverWait(driver, 10)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                break
            except:
                continue
        
        # Se não encontrou botão, tenta clicar no número da próxima página
        if not next_button:
            try:
                # Procura pelo número da próxima página (pagina_atual + 1)
                next_page_num = pagina_atual + 1
                page_link = driver.find_element(By.XPATH, f"//a[contains(text(), '{next_page_num}')]")
                if page_link and page_link.is_enabled():
                    next_button = page_link
            except:
                pass
        
        if next_button and next_button.is_enabled():
            next_button.click()
            time.sleep(2)  # Espera a página carregar
            
            # Salva o progresso a cada 10 páginas
            if pagina_atual % 10 == 0:
                df_progresso = pd.DataFrame(dados, columns=[
                    "OS", "Cliente", "Vendedor", "Data Abertura", "Defeito", "Equipamento", "OBS"
                ])
                df_progresso.to_excel("os_extraidas.xlsx", index=False)
                with open("ultima_pagina.txt", "w") as f:
                    f.write(str(pagina_atual))
                print(f"Progresso salvo: página {pagina_atual}")
            
            pagina_atual += 1
        else:
            print("Não há mais páginas para navegar.")
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
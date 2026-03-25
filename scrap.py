from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import pandas as pd
import time

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Edge(options=options)

print("Conectado com sucesso!")

time.sleep(3)

# pega todas as linhas da tabela
rows = driver.find_elements(By.CSS_SELECTOR, "table tr")

dados = []

for i in range(len(rows)):
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    row = rows[i]

    cols = row.find_elements(By.TAG_NAME, "td")
    
    if len(cols) >= 6:
        try:
            numero_os = cols[1].text
            cliente = cols[2].text
            vendedor = cols[3].text
            data_abertura = cols[4].text
            defeito = cols[5].text
            equipamento = cols[6].text if len(cols) > 6 else ""
            obs = cols[7].text if len(cols) > 7 else ""

            dados.append([
                numero_os,
                cliente,
                vendedor,
                data_abertura,
                defeito,
                equipamento,
                obs
            ])
        except:
            continue

df = pd.DataFrame(dados, columns=[
    "OS",
    "Cliente",
    "Vendedor",
    "Data Abertura",
    "Defeito",
    "Equipamento",
    "OBS"
])

print(df)

df.to_excel("os_extraidas.xlsx", index=False)

driver.quit()
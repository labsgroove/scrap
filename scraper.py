"""
Módulo de scraping com retentativas automáticas e tratamento robusto de erros.
"""
import logging
import re
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple, Callable
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException
)
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
    before_sleep_log
)

from models import ServiceOrder, ScrapingConfig, ScrapingResult

logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Exceção base para erros de scraping"""
    pass


class TableNotFoundError(ScrapingError):
    """Tabela não encontrada na página"""
    pass


class PaginationError(ScrapingError):
    """Erro ao detectar ou navegar paginação"""
    pass


class TextExtractor:
    """Extrator de texto com múltiplas estratégias de fallback"""
    
    @staticmethod
    def extract(element: WebElement) -> str:
        """Extrai texto limpo de um elemento com múltiplas estratégias"""
        try:
            # Estratégia 1: texto direto
            texto = element.text.strip()
            if texto:
                return TextExtractor._clean(texto)
            
            # Estratégia 2: atributo title
            title = element.get_attribute("title")
            if title:
                return TextExtractor._clean(title)
            
            # Estratégia 3: innerHTML limpo
            html = element.get_attribute("innerHTML")
            if html:
                texto = re.sub(r'<[^>]+>', ' ', html).strip()
                texto = texto.replace('&nbsp;', ' ').replace('&amp;', '&')
                return TextExtractor._clean(texto)
            
            # Estratégia 4: procura elementos filhos
            filhos = element.find_elements(By.XPATH, ".//*")
            for filho in filhos:
                txt = filho.text.strip()
                if txt:
                    return TextExtractor._clean(txt)
            
            return ""
        except StaleElementReferenceException:
            logger.warning("Elemento obsoleto ao extrair texto")
            return ""
        except Exception as e:
            logger.debug(f"Erro ao extrair texto: {e}")
            return ""
    
    @staticmethod
    def _clean(text: str) -> str:
        """Normaliza espaços e quebras de linha"""
        if not text:
            return ""
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class PaginationDetector:
    """Detector de paginação com múltiplas estratégias"""
    
    PATTERNS = [
        r'[Pp][áa]gina\s*(\d+)\s*/\s*(\d+)',
        r'(\d+)\s*/\s*(\d+)',
        r'(\d+)\s+de\s+(\d+)',
    ]
    
    XPATH_STRATEGIES = [
        "//span[contains(@class, 'pagina')]",
        "//div[contains(@class, 'paginacao')]",
        "//div[contains(@class, 'pagination')]",
        "//a[contains(@class, 'linklist')]",
        "//span[contains(@class, 'page')]",
        "//td[contains(text(), 'Página')]",
        "//td[contains(text(), 'Pagina')]",
    ]
    
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def detect(self) -> Tuple[Optional[int], Optional[int]]:
        """Detecta página atual e total de páginas"""
        try:
            # Estratégia 1: XPath por classes comuns
            for xpath in self.XPATH_STRATEGIES:
                try:
                    elems = self.driver.find_elements(By.XPATH, xpath)
                    for elem in elems:
                        texto = elem.text
                        result = self._parse_pagination(texto)
                        if result:
                            return result
                except Exception:
                    continue
            
            # Estratégia 2: Busca por texto contendo números
            try:
                page_elements = self.driver.find_elements(
                    By.XPATH, "//*[contains(text(), '/')]"
                )
                for elem in page_elements:
                    texto = elem.text
                    if 'pagina' in texto.lower() or 'página' in texto.lower():
                        result = self._parse_pagination(texto)
                        if result:
                            return result
            except Exception:
                pass
                
        except Exception as e:
            self.logger.debug(f"Erro ao detectar paginação: {e}")
        
        return None, None
    
    def _parse_pagination(self, text: str) -> Optional[Tuple[int, int]]:
        """Extrai números de página de um texto"""
        if not text:
            return None
        
        for pattern in self.PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    if total > 0 and current > 0 and current <= total:
                        return current, total
                except (ValueError, IndexError):
                    continue
        return None


class ServiceOrderScraper:
    """Scraper profissional de Ordens de Serviço com retentativas"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver: Optional[webdriver.Remote] = None
        self.pagination_detector: Optional[PaginationDetector] = None
        self._shutdown_requested = False
    
    def _create_driver(self) -> webdriver.Remote:
        """Cria e configura o driver do Edge"""
        options = EdgeOptions()
        
        if self.config.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Conecta ao browser existente ou cria novo
        if self.config.debugger_address:
            options.add_experimental_option(
                "debuggerAddress", self.config.debugger_address
            )
            driver = webdriver.Edge(options=options)
            self.logger.info(f"Conectado ao browser em {self.config.debugger_address}")
        else:
            driver = webdriver.Edge(options=options)
            self.logger.info("Novo browser iniciado")
        
        # Remove flag de webdriver
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        return driver
    
    @contextmanager
    def _managed_driver(self):
        """Context manager para gerenciar o driver"""
        try:
            self.driver = self._create_driver()
            self.pagination_detector = PaginationDetector(self.driver)
            yield self.driver
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.warning(f"Erro ao fechar driver: {e}")
                self.driver = None
    
    @retry(
        retry=retry_if_exception_type((TimeoutException, WebDriverException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _wait_for_table(self) -> WebElement:
        """Aguarda tabela carregar com retentativas"""
        wait = WebDriverWait(self.driver, self.config.timeout)
        return wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )
    
    @retry(
        retry=retry_if_exception_type(StaleElementReferenceException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3)
    )
    def _get_rows(self) -> List[WebElement]:
        """Obtém linhas da tabela com retentativas"""
        return self.driver.find_elements(
            By.CSS_SELECTOR, "table tbody tr, table tr"
        )
    
    def _extract_row_data(self, row: WebElement) -> Optional[ServiceOrder]:
        """Extrai dados de uma linha da tabela"""
        try:
            colunas = row.find_elements(By.TAG_NAME, "td")
            num_cols = len(colunas)
            
            if num_cols < 6:
                return None
            
            os_num = TextExtractor.extract(colunas[1]) if num_cols > 1 else ""
            cliente = TextExtractor.extract(colunas[2]) if num_cols > 2 else ""
            vendedor = TextExtractor.extract(colunas[3]) if num_cols > 3 else ""
            data_abertura = TextExtractor.extract(colunas[4]) if num_cols > 4 else ""
            status = TextExtractor.extract(colunas[5]) if num_cols > 5 else ""
            equipamento = TextExtractor.extract(colunas[6]) if num_cols > 6 else ""
            obs = TextExtractor.extract(colunas[7]) if num_cols > 7 else ""
            
            # Só cria registro se tiver número de OS válido
            if os_num and re.match(r'^[\d\-/]+$', os_num):
                return ServiceOrder(
                    os_number=os_num,
                    cliente=cliente,
                    vendedor=vendedor,
                    data_abertura=data_abertura,
                    status=status,
                    equipamento=equipamento,
                    observacao=obs
                )
        except StaleElementReferenceException:
            self.logger.debug("Elemento obsoleto ao extrair linha")
        except Exception as e:
            self.logger.debug(f"Erro ao extrair linha: {e}")
        
        return None
    
    def _wait_for_page_change(self, previous_page: int, 
                              progress_callback: Optional[Callable] = None) -> int:
        """Aguarda mudança de página com timeout"""
        start_time = time.time()
        tentativas = 0
        
        while time.time() - start_time < self.config.max_wait_time:
            if self._shutdown_requested:
                return previous_page
            
            time.sleep(self.config.wait_between_pages)
            tentativas += 1
            
            nova_pagina, _ = self.pagination_detector.detect()
            if nova_pagina and nova_pagina != previous_page:
                return nova_pagina
            
            if progress_callback and tentativas % 10 == 0:
                progress_callback(tentativas)
        
        raise PaginationError(
            f"Timeout aguardando mudança de página após {self.config.max_wait_time}s"
        )
    
    def scrape(self, start_page: int = 1, 
               progress_callback: Optional[Callable] = None,
               stop_check: Optional[Callable] = None) -> Tuple[ScrapingResult, List[ServiceOrder]]:
        """
        Executa o scraping completo com retentativas e tratamento de erros.
        
        Args:
            start_page: Página inicial para começar
            progress_callback: Função chamada a cada 10s de espera (recebe tentativas)
            stop_check: Função que retorna True para parar o processamento
            
        Returns:
            Tuple de (ScrapingResult, List[ServiceOrder])
        """
        result = ScrapingResult(
            total_records=0,
            pages_processed=0,
            errors=[],
            start_time=datetime.now()
        )
        
        dados: List[ServiceOrder] = []
        pagina_atual = start_page
        
        with self._managed_driver():
            self.logger.info(f"Iniciando scraping da página {start_page}")
            
            while not self._shutdown_requested:
                if stop_check and stop_check():
                    self.logger.info("Parada solicitada externamente")
                    break
                
                try:
                    registros = self._process_page(pagina_atual, dados)
                    result.total_records += registros
                    result.pages_processed += 1
                    
                    self.logger.info(
                        f"Página {pagina_atual}: {registros} registros "
                        f"(total: {result.total_records})"
                    )
                    
                    pagina_detectada, total_paginas = self.pagination_detector.detect()
                    if pagina_detectada and total_paginas:
                        self.logger.info(f"Paginação: {pagina_detectada}/{total_paginas}")
                        if pagina_detectada >= total_paginas:
                            self.logger.info("Última página alcançada")
                            break
                    
                    self.logger.info("Aguardando avanço de página...")
                    try:
                        nova_pagina = self._wait_for_page_change(pagina_atual, progress_callback)
                        pagina_atual = nova_pagina
                    except PaginationError as e:
                        self.logger.warning(f"{e}. Continuando.")
                        pagina_atual += 1
                        
                except Exception as e:
                    error_msg = f"Erro página {pagina_atual}: {str(e)}"
                    self.logger.error(error_msg)
                    result.errors.append(error_msg)
                    
                    if len(result.errors) >= self.config.max_retries:
                        self.logger.error("Máximo de erros atingido.")
                        break
                    
                    time.sleep(self.config.retry_delay)
                    continue
        
        result.end_time = datetime.now()
        self.logger.info(
            f"Scraping finalizado: {result.total_records} registros em "
            f"{result.pages_processed} páginas ({result.duration:.1f}s)"
        )
        
        return result, dados
    
    def _process_page(self, page: int, dados: List[ServiceOrder]) -> int:
        """Processa uma página e retorna quantidade de registros extraídos"""
        try:
            tabela = self._wait_for_table()
            self.logger.debug(f"Tabela encontrada na página {page}")
            
            linhas = self._get_rows()
            self.logger.debug(f"Encontradas {len(linhas)} linhas")
            
            registros = 0
            for i, linha in enumerate(linhas[1:] if len(linhas) > 1 else linhas):
                if self._shutdown_requested:
                    break
                
                try:
                    service_order = self._extract_row_data(linha)
                    if service_order:
                        dados.append(service_order)
                        registros += 1
                        
                        if registros == 1:
                            self.logger.debug(f"Exemplo: {service_order.to_dict()}")
                            
                except Exception as e:
                    self.logger.debug(f"Erro linha {i}: {e}")
                    continue
            
            return registros
            
        except TimeoutException:
            raise TableNotFoundError(f"Tabela não encontrada na página {page}")
        except Exception as e:
            raise ScrapingError(f"Erro processando página {page}: {e}")
    
    def request_shutdown(self):
        """Solicita parada graceful do scraping"""
        self._shutdown_requested = True
        self.logger.info("Shutdown solicitado")

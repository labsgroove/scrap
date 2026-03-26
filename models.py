from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re


class ServiceOrder(BaseModel):
    """Modelo de validação para Ordens de Serviço"""
    os_number: str = Field(..., description="Número da OS")
    cliente: str = Field(default="", description="Nome do cliente")
    vendedor: str = Field(default="", description="Nome do vendedor")
    data_abertura: str = Field(default="", description="Data de abertura")
    status: str = Field(default="", description="Status da OS")
    equipamento: str = Field(default="", description="Equipamento")
    observacao: str = Field(default="", description="Observação")
    
    @validator('os_number')
    def validate_os_number(cls, v):
        """Valida que o número da OS contém apenas dígitos"""
        if v and not re.match(r'^[\d\-/]+$', str(v)):
            raise ValueError(f'Número de OS inválido: {v}')
        return v.strip() if v else v
    
    @validator('cliente', 'vendedor', 'equipamento', 'observacao')
    def clean_text(cls, v):
        """Limpa espaços excessivos do texto"""
        if v:
            return re.sub(r'\s+', ' ', v).strip()
        return v
    
    def to_dict(self) -> dict:
        return {
            "OS": self.os_number,
            "Cliente": self.cliente,
            "Vendedor": self.vendedor,
            "Data Abertura": self.data_abertura,
            "Status": self.status,
            "Equipamento": self.equipamento,
            "OBS": self.observacao
        }


@dataclass
class ScrapingConfig:
    """Configuração para o scraper"""
    debugger_address: str = "127.0.0.1:9222"
    output_file: str = "os_extraidas.xlsx"
    checkpoint_file: str = "ultima_pagina.txt"
    headless: bool = False
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    wait_between_pages: float = 1.0
    max_wait_time: int = 300  # 5 minutos máximo esperando página


@dataclass
class ScrapingResult:
    """Resultado do processamento"""
    total_records: int
    pages_processed: int
    errors: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if not self.errors:
            return 100.0
        # Estimativa baseada em erros vs páginas
        return max(0, 100 - (len(self.errors) * 10))

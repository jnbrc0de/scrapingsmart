from typing import Dict, Any, Optional, List, Union, Callable
import time
import logging
import json
import os
from datetime import datetime, timedelta
from threading import Lock
from pathlib import Path
import threading

# Verificação condicional para importação do prometheus_client
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

class MetricsEvent:
    """Representa um evento de métrica."""
    def __init__(self, 
                event_type: str,
                category: str,
                value: Union[float, int, bool, str],
                labels: Optional[Dict[str, str]] = None,
                timestamp: Optional[datetime] = None):
        self.event_type = event_type
        self.category = category
        self.value = value
        self.labels = labels or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o evento para um dicionário."""
        return {
            'event_type': self.event_type,
            'category': self.category,
            'value': self.value,
            'labels': self.labels,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricsEvent':
        """Cria um evento a partir de um dicionário."""
        return cls(
            event_type=data['event_type'],
            category=data['category'],
            value=data['value'],
            labels=data['labels'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

class MetricsManager:
    """
    Gerenciador unificado de métricas.
    
    Suporta:
    - Métricas em memória
    - Métricas em arquivo
    - Exportação para Prometheus
    - Notificações baseadas em eventos
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o gerenciador de métricas.
        
        Args:
            config: Configuração das métricas
                prometheus_enabled: bool - Se a exportação para Prometheus está habilitada
                prometheus_port: int - Porta do servidor Prometheus
                file_enabled: bool - Se o armazenamento em arquivo está habilitado
                file_path: str - Caminho para o arquivo de métricas
                history_size: int - Tamanho máximo do histórico em memória
                retention_days: int - Dias de retenção para métricas em arquivo
        """
        # Configuração padrão
        self.config = {
            'prometheus_enabled': PROMETHEUS_AVAILABLE,
            'prometheus_port': 8000,
            'file_enabled': True,
            'file_path': 'data/metrics',
            'history_size': 1000,
            'retention_days': 7,
            'alert_thresholds': {
                'error_rate': 0.2,  # 20%
                'block_rate': 0.1,  # 10%
                'captcha_rate': 0.1,  # 10%
                'memory_percent': 80.0,  # 80%
                'cpu_percent': 80.0  # 80%
            }
        }
        
        # Atualiza com configurações fornecidas
        if config:
            self.config.update(config)
            
        # Inicialização
        self.logger = logging.getLogger("metrics_manager")
        self._lock = Lock()
        self._events: List[MetricsEvent] = []
        self._counters: Dict[str, Dict[str, float]] = {}
        self._gauges: Dict[str, Dict[str, float]] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Inicializa armazenamento em arquivo
        if self.config['file_enabled']:
            self.metrics_path = Path(self.config['file_path'])
            self.metrics_path.mkdir(parents=True, exist_ok=True)
            
        # Inicializa Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            self._setup_prometheus()
            
        # Inicia thread de exportação periódica
        self._export_thread = threading.Thread(
            target=self._periodic_export,
            daemon=True
        )
        self._export_thread.start()
            
    def _setup_prometheus(self) -> None:
        """Configura métricas do Prometheus."""
        try:
            # Métricas de extração
            self._prom_extraction_total = Counter(
                'scraper_extraction_total',
                'Total de extrações realizadas',
                ['strategy', 'status']
            )
            
            self._prom_extraction_duration = Histogram(
                'scraper_extraction_duration_seconds',
                'Duração das extrações em segundos',
                ['strategy'],
                buckets=(1, 2, 5, 10, 30, 60, 120, 300)
            )
            
            self._prom_extraction_confidence = Gauge(
                'scraper_extraction_confidence',
                'Confiança da última extração',
                ['strategy']
            )
            
            # Métricas de erro
            self._prom_error_total = Counter(
                'scraper_error_total',
                'Total de erros encontrados',
                ['strategy', 'error_type']
            )
            
            # Métricas de bloqueio
            self._prom_block_total = Counter(
                'scraper_block_total',
                'Total de bloqueios encontrados',
                ['strategy']
            )
            
            # Métricas de CAPTCHA
            self._prom_captcha_total = Counter(
                'scraper_captcha_total',
                'Total de CAPTCHAs encontrados',
                ['strategy']
            )
            
            # Métricas de cache
            self._prom_cache_hits = Counter(
                'scraper_cache_hits_total',
                'Total de hits no cache',
                ['strategy']
            )
            
            self._prom_cache_misses = Counter(
                'scraper_cache_misses_total',
                'Total de misses no cache',
                ['strategy']
            )
            
            # Métricas de recursos
            self._prom_memory_usage = Gauge(
                'scraper_memory_usage_bytes',
                'Uso de memória em bytes'
            )
            
            self._prom_cpu_usage = Gauge(
                'scraper_cpu_usage_percent',
                'Uso de CPU em percentual'
            )
            
            # Inicia servidor
            start_http_server(self.config['prometheus_port'])
            self.logger.info(f"Servidor Prometheus iniciado na porta {self.config['prometheus_port']}")
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar Prometheus: {str(e)}")
            self.config['prometheus_enabled'] = False
            
    def register_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Registra uma callback para alertas.
        
        Args:
            callback: Função que recebe o tipo de alerta e dados contextuais
        """
        with self._lock:
            self._alert_callbacks.append(callback)
            
    def record_extraction(self, strategy: str, success: bool, duration: float, 
                         confidence: Optional[float] = None) -> None:
        """
        Registra métricas de uma extração.
        
        Args:
            strategy: Nome da estratégia
            success: Se a extração foi bem-sucedida
            duration: Duração da extração em segundos
            confidence: Confiança da extração (opcional)
        """
        # Registra evento
        event = MetricsEvent(
            event_type='extraction',
            category='scraping',
            value=duration,
            labels={
                'strategy': strategy,
                'success': str(success),
                'confidence': str(confidence) if confidence is not None else 'null'
            }
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza contadores
            counter_key = f"extraction_{strategy}_{'success' if success else 'failure'}"
            self._increment_counter(counter_key, 1)
            
            # Atualiza histograma
            histogram_key = f"duration_{strategy}"
            if histogram_key not in self._histograms:
                self._histograms[histogram_key] = []
            self._histograms[histogram_key].append(duration)
            
            # Atualiza gauge de confiança
            if confidence is not None:
                gauge_key = f"confidence_{strategy}"
                self._set_gauge(gauge_key, confidence)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                self._prom_extraction_total.labels(
                    strategy=strategy,
                    status='success' if success else 'failure'
                ).inc()
                
                self._prom_extraction_duration.labels(
                    strategy=strategy
                ).observe(duration)
                
                if confidence is not None:
                    self._prom_extraction_confidence.labels(
                        strategy=strategy
                    ).set(confidence)
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
        # Verifica alertas
        self._check_extraction_alerts(strategy)
                
    def record_error(self, strategy: str, error_type: str) -> None:
        """
        Registra métricas de erro.
        
        Args:
            strategy: Nome da estratégia
            error_type: Tipo do erro
        """
        # Registra evento
        event = MetricsEvent(
            event_type='error',
            category='error',
            value=1,
            labels={
                'strategy': strategy,
                'error_type': error_type
            }
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza contadores
            counter_key = f"error_{strategy}_{error_type}"
            self._increment_counter(counter_key, 1)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                self._prom_error_total.labels(
                    strategy=strategy,
                    error_type=error_type
                ).inc()
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
    def record_block(self, strategy: str) -> None:
        """
        Registra métricas de bloqueio.
        
        Args:
            strategy: Nome da estratégia
        """
        # Registra evento
        event = MetricsEvent(
            event_type='block',
            category='security',
            value=1,
            labels={
                'strategy': strategy
            }
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza contadores
            counter_key = f"block_{strategy}"
            self._increment_counter(counter_key, 1)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                self._prom_block_total.labels(
                    strategy=strategy
                ).inc()
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
        # Verifica alertas
        self._check_block_alerts(strategy)
                
    def record_captcha(self, strategy: str) -> None:
        """
        Registra métricas de CAPTCHA.
        
        Args:
            strategy: Nome da estratégia
        """
        # Registra evento
        event = MetricsEvent(
            event_type='captcha',
            category='security',
            value=1,
            labels={
                'strategy': strategy
            }
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza contadores
            counter_key = f"captcha_{strategy}"
            self._increment_counter(counter_key, 1)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                self._prom_captcha_total.labels(
                    strategy=strategy
                ).inc()
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
        # Verifica alertas
        self._check_captcha_alerts(strategy)
                
    def record_cache(self, strategy: str, hit: bool) -> None:
        """
        Registra métricas de cache.
        
        Args:
            strategy: Nome da estratégia
            hit: Se foi hit (True) ou miss (False)
        """
        # Registra evento
        event = MetricsEvent(
            event_type='cache',
            category='performance',
            value=1 if hit else 0,
            labels={
                'strategy': strategy,
                'hit': str(hit)
            }
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza contadores
            counter_key = f"cache_{strategy}_{'hit' if hit else 'miss'}"
            self._increment_counter(counter_key, 1)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                if hit:
                    self._prom_cache_hits.labels(
                        strategy=strategy
                    ).inc()
                else:
                    self._prom_cache_misses.labels(
                        strategy=strategy
                    ).inc()
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
    def update_resources(self, memory_bytes: int, cpu_percent: float) -> None:
        """
        Atualiza métricas de recursos.
        
        Args:
            memory_bytes: Uso de memória em bytes
            cpu_percent: Uso de CPU em percentual
        """
        # Registra evento
        event = MetricsEvent(
            event_type='resources',
            category='system',
            value={
                'memory_bytes': memory_bytes,
                'cpu_percent': cpu_percent
            },
            labels={}
        )
        
        with self._lock:
            self._events.append(event)
            
            # Atualiza gauges
            self._set_gauge('memory_bytes', memory_bytes)
            self._set_gauge('cpu_percent', cpu_percent)
                
        # Atualiza Prometheus
        if self.config['prometheus_enabled'] and PROMETHEUS_AVAILABLE:
            try:
                self._prom_memory_usage.set(memory_bytes)
                self._prom_cpu_usage.set(cpu_percent)
            except Exception as e:
                self.logger.error(f"Erro ao registrar métricas no Prometheus: {str(e)}")
                
        # Verifica alertas
        self._check_resource_alerts(memory_bytes, cpu_percent)
                
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Retorna um resumo das métricas.
        
        Returns:
            Dicionário com resumo das métricas
        """
        with self._lock:
            # Calcula estatísticas
            extractions_total = sum(v for k, v in self._counters.items() if k.startswith('extraction_'))
            extractions_success = sum(v for k, v in self._counters.items() if k.startswith('extraction_') and k.endswith('_success'))
            extractions_failure = sum(v for k, v in self._counters.items() if k.startswith('extraction_') and k.endswith('_failure'))
            
            errors_total = sum(v for k, v in self._counters.items() if k.startswith('error_'))
            blocks_total = sum(v for k, v in self._counters.items() if k.startswith('block_'))
            captchas_total = sum(v for k, v in self._counters.items() if k.startswith('captcha_'))
            
            cache_hits = sum(v for k, v in self._counters.items() if k.startswith('cache_') and k.endswith('_hit'))
            cache_misses = sum(v for k, v in self._counters.items() if k.startswith('cache_') and k.endswith('_miss'))
            
            # Calcula estatísticas por estratégia
            strategies = set()
            for key in self._counters.keys():
                if key.startswith('extraction_'):
                    strategy = key.split('_')[1]
                    strategies.add(strategy)
                    
            strategy_stats = {}
            for strategy in strategies:
                success = self._counters.get(f'extraction_{strategy}_success', 0)
                failure = self._counters.get(f'extraction_{strategy}_failure', 0)
                total = success + failure
                
                strategy_stats[strategy] = {
                    'extractions': {
                        'total': total,
                        'success': success,
                        'failure': failure,
                        'success_rate': success / total if total > 0 else 0
                    },
                    'errors': self._counters.get(f'error_{strategy}', 0),
                    'blocks': self._counters.get(f'block_{strategy}', 0),
                    'captchas': self._counters.get(f'captcha_{strategy}', 0),
                    'cache': {
                        'hits': self._counters.get(f'cache_{strategy}_hit', 0),
                        'misses': self._counters.get(f'cache_{strategy}_miss', 0)
                    }
                }
                
                # Adiciona estatísticas de duração
                duration_key = f'duration_{strategy}'
                if duration_key in self._histograms and self._histograms[duration_key]:
                    durations = self._histograms[duration_key]
                    strategy_stats[strategy]['duration'] = {
                        'avg': sum(durations) / len(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'p50': self._percentile(durations, 50),
                        'p90': self._percentile(durations, 90),
                        'p95': self._percentile(durations, 95),
                        'p99': self._percentile(durations, 99)
                    }
                
            # Obtém métricas de recurso atuais
            try:
                import psutil
                process = psutil.Process()
                memory_bytes = process.memory_info().rss
                cpu_percent = process.cpu_percent(interval=0.1)
            except ImportError:
                memory_bytes = self._gauges.get('memory_bytes', 0)
                cpu_percent = self._gauges.get('cpu_percent', 0)
                
            return {
                'extractions': {
                    'total': extractions_total,
                    'success': extractions_success,
                    'failure': extractions_failure,
                    'success_rate': extractions_success / extractions_total if extractions_total > 0 else 0
                },
                'errors': errors_total,
                'security': {
                    'blocks': blocks_total,
                    'captchas': captchas_total
                },
                'cache': {
                    'hits': cache_hits,
                    'misses': cache_misses,
                    'hit_rate': cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
                },
                'resources': {
                    'memory_mb': round(memory_bytes / (1024 * 1024), 2),
                    'cpu_percent': cpu_percent
                },
                'strategies': strategy_stats,
                'events_tracked': len(self._events)
            }
            
    def export_metrics(self) -> bool:
        """
        Exporta métricas para arquivo.
        
        Returns:
            True se exportado com sucesso, False caso contrário
        """
        if not self.config['file_enabled']:
            return False
            
        try:
            # Gera nome do arquivo baseado na data
            today = datetime.now().strftime('%Y-%m-%d')
            filepath = self.metrics_path / f"metrics_{today}.json"
            
            # Converte eventos para dicionários
            with self._lock:
                events = [e.to_dict() for e in self._events]
                
            # Verifica se arquivo existe
            if filepath.exists():
                # Carrega dados existentes
                with open(filepath, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except:
                        data = []
                        
                # Adiciona novos eventos
                data.extend(events)
            else:
                data = events
                
            # Salva arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # Limpa eventos
            with self._lock:
                self._events = []
                
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao exportar métricas: {str(e)}")
            return False
            
    def cleanup_old_metrics(self) -> int:
        """
        Remove arquivos de métricas antigos.
        
        Returns:
            Número de arquivos removidos
        """
        if not self.config['file_enabled']:
            return 0
            
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['retention_days'])
            count = 0
            
            for filepath in self.metrics_path.glob("metrics_*.json"):
                try:
                    # Extrai data do nome do arquivo
                    date_str = filepath.stem.replace('metrics_', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Verifica se é antigo
                    if file_date < cutoff_date:
                        filepath.unlink()
                        count += 1
                except:
                    continue
                    
            return count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar métricas antigas: {str(e)}")
            return 0
            
    def _periodic_export(self) -> None:
        """Exporta métricas periodicamente."""
        while True:
            try:
                # Exporta métricas a cada hora
                time.sleep(3600)
                self.export_metrics()
                self.cleanup_old_metrics()
            except:
                pass
                
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calcula percentil de uma lista de valores."""
        if not values:
            return 0
            
        values = sorted(values)
        idx = (len(values) - 1) * percentile / 100
        
        if idx.is_integer():
            return values[int(idx)]
        else:
            lower = values[int(idx)]
            upper = values[int(idx) + 1]
            return lower + (upper - lower) * (idx - int(idx))
            
    def _increment_counter(self, key: str, value: float = 1) -> None:
        """Incrementa um contador."""
        if key not in self._counters:
            self._counters[key] = 0
        self._counters[key] += value
        
    def _set_gauge(self, key: str, value: float) -> None:
        """Define valor de um gauge."""
        self._gauges[key] = value
        
    def _check_extraction_alerts(self, strategy: str) -> None:
        """Verifica alertas baseados em extrações."""
        with self._lock:
            # Calcula taxa de erro
            success = self._counters.get(f'extraction_{strategy}_success', 0)
            failure = self._counters.get(f'extraction_{strategy}_failure', 0)
            total = success + failure
            
            if total >= 10:  # Precisamos de pelo menos 10 extrações para avaliar
                error_rate = failure / total
                
                # Verifica se acima do limiar
                if error_rate >= self.config['alert_thresholds']['error_rate']:
                    # Dispara alerta
                    self._send_alert(
                        'high_error_rate',
                        {
                            'strategy': strategy,
                            'error_rate': error_rate,
                            'threshold': self.config['alert_thresholds']['error_rate'],
                            'total_attempts': total
                        }
                    )
                    
    def _check_block_alerts(self, strategy: str) -> None:
        """Verifica alertas baseados em bloqueios."""
        with self._lock:
            # Calcula taxa de bloqueio
            blocks = self._counters.get(f'block_{strategy}', 0)
            total = sum(v for k, v in self._counters.items() 
                       if k.startswith(f'extraction_{strategy}'))
            
            if total >= 10:  # Precisamos de pelo menos 10 extrações para avaliar
                block_rate = blocks / total
                
                # Verifica se acima do limiar
                if block_rate >= self.config['alert_thresholds']['block_rate']:
                    # Dispara alerta
                    self._send_alert(
                        'high_block_rate',
                        {
                            'strategy': strategy,
                            'block_rate': block_rate,
                            'threshold': self.config['alert_thresholds']['block_rate'],
                            'total_attempts': total
                        }
                    )
                    
    def _check_captcha_alerts(self, strategy: str) -> None:
        """Verifica alertas baseados em CAPTCHAs."""
        with self._lock:
            # Calcula taxa de CAPTCHA
            captchas = self._counters.get(f'captcha_{strategy}', 0)
            total = sum(v for k, v in self._counters.items() 
                       if k.startswith(f'extraction_{strategy}'))
            
            if total >= 10:  # Precisamos de pelo menos 10 extrações para avaliar
                captcha_rate = captchas / total
                
                # Verifica se acima do limiar
                if captcha_rate >= self.config['alert_thresholds']['captcha_rate']:
                    # Dispara alerta
                    self._send_alert(
                        'high_captcha_rate',
                        {
                            'strategy': strategy,
                            'captcha_rate': captcha_rate,
                            'threshold': self.config['alert_thresholds']['captcha_rate'],
                            'total_attempts': total
                        }
                    )
                    
    def _check_resource_alerts(self, memory_bytes: int, cpu_percent: float) -> None:
        """Verifica alertas baseados em recursos."""
        # Verifica uso de memória
        try:
            import psutil
            total_memory = psutil.virtual_memory().total
            memory_percent = memory_bytes / total_memory * 100
            
            # Verifica se acima do limiar
            if memory_percent >= self.config['alert_thresholds']['memory_percent']:
                # Dispara alerta
                self._send_alert(
                    'high_memory_usage',
                    {
                        'memory_percent': memory_percent,
                        'memory_mb': round(memory_bytes / (1024 * 1024), 2),
                        'threshold': self.config['alert_thresholds']['memory_percent']
                    }
                )
        except:
            pass
            
        # Verifica uso de CPU
        if cpu_percent >= self.config['alert_thresholds']['cpu_percent']:
            # Dispara alerta
            self._send_alert(
                'high_cpu_usage',
                {
                    'cpu_percent': cpu_percent,
                    'threshold': self.config['alert_thresholds']['cpu_percent']
                }
            )
            
    def _send_alert(self, alert_type: str, details: Dict[str, Any]) -> None:
        """Envia alerta para callbacks registrados."""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, details)
            except Exception as e:
                self.logger.error(f"Erro ao enviar alerta: {str(e)}") 
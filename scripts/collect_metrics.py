#!/usr/bin/env python3
"""Script to collect and aggregate metrics from Docker containers."""

import os
import json
import time
import docker
import psutil
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/var/log/umbrella/metrics.log'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    """Container for service metrics."""
    cpu_usage: float
    memory_usage: float
    memory_limit: float
    disk_read: float
    disk_write: float
    network_rx: float
    network_tx: float
    response_time: float

class MetricsCollector:
    """Collects and aggregates metrics from Docker containers."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.docker_client = docker.from_env()
        self.services = [
            "pdf_extraction",
            "sentiment_analysis",
            "rag_scraper",
            "chatbot",
            "api_gateway"
        ]
        self.metrics_file = "/var/log/umbrella/container_metrics.json"
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()

    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics."""
        self.cpu_gauge = Gauge(
            'container_cpu_usage',
            'Container CPU Usage Percentage',
            ['service'],
            registry=self.registry
        )
        self.memory_gauge = Gauge(
            'container_memory_usage',
            'Container Memory Usage Bytes',
            ['service'],
            registry=self.registry
        )
        self.response_time_gauge = Gauge(
            'service_response_time',
            'Service Response Time Seconds',
            ['service'],
            registry=self.registry
        )

    def collect_container_metrics(self, container_name: str) -> ServiceMetrics:
        """Collect metrics for a specific container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            ServiceMetrics: Container metrics
        """
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                         stats['precpu_stats']['system_cpu_usage']
            cpu_usage = (cpu_delta / system_delta) * 100.0
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            # Disk I/O
            disk_stats = stats['blkio_stats']['io_service_bytes_recursive']
            disk_read = sum(stat['value'] for stat in disk_stats if stat['op'] == 'Read')
            disk_write = sum(stat['value'] for stat in disk_stats if stat['op'] == 'Write')
            
            # Network I/O
            network_stats = stats['networks']['eth0']
            network_rx = network_stats['rx_bytes']
            network_tx = network_stats['tx_bytes']
            
            # Service response time
            port = self._get_service_port(container_name)
            response_time = self._measure_response_time(f"http://localhost:{port}/health")
            
            return ServiceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                disk_read=disk_read,
                disk_write=disk_write,
                network_rx=network_rx,
                network_tx=network_tx,
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for {container_name}: {str(e)}")
            return None

    def _get_service_port(self, service_name: str) -> int:
        """Get port number for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            int: Port number
        """
        port_mapping = {
            "pdf_extraction": 8001,
            "sentiment_analysis": 8002,
            "rag_scraper": 8003,
            "chatbot": 8004,
            "api_gateway": 8000
        }
        return port_mapping.get(service_name, 8000)

    def _measure_response_time(self, url: str) -> float:
        """Measure response time for a service endpoint.
        
        Args:
            url: Service endpoint URL
            
        Returns:
            float: Response time in seconds
        """
        try:
            start_time = time.time()
            requests.get(url, timeout=5)
            return time.time() - start_time
        except Exception as e:
            logger.warning(f"Failed to measure response time for {url}: {str(e)}")
            return -1

    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-wide metrics.
        
        Returns:
            Dict[str, float]: System metrics
        """
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage("/").percent,
            "network_bytes_sent": psutil.net_io_counters().bytes_sent,
            "network_bytes_recv": psutil.net_io_counters().bytes_recv
        }

    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect metrics for all services.
        
        Returns:
            Dict[str, Any]: All metrics
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": self.collect_system_metrics(),
            "services": {}
        }
        
        for service in self.services:
            service_metrics = self.collect_container_metrics(service)
            if service_metrics:
                metrics["services"][service] = {
                    "cpu_usage": service_metrics.cpu_usage,
                    "memory_usage": service_metrics.memory_usage,
                    "memory_limit": service_metrics.memory_limit,
                    "disk_read": service_metrics.disk_read,
                    "disk_write": service_metrics.disk_write,
                    "network_rx": service_metrics.network_rx,
                    "network_tx": service_metrics.network_tx,
                    "response_time": service_metrics.response_time
                }
                
                # Update Prometheus metrics
                self.cpu_gauge.labels(service=service).set(service_metrics.cpu_usage)
                self.memory_gauge.labels(service=service).set(service_metrics.memory_usage)
                self.response_time_gauge.labels(service=service).set(service_metrics.response_time)
        
        return metrics

    def save_metrics(self, metrics: Dict[str, Any]):
        """Save metrics to file.
        
        Args:
            metrics: Metrics to save
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            
            # Load existing metrics
            existing_metrics = []
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    existing_metrics = json.load(f)
            
            # Append new metrics
            existing_metrics.append(metrics)
            
            # Keep only last 1000 entries
            if len(existing_metrics) > 1000:
                existing_metrics = existing_metrics[-1000:]
            
            # Save updated metrics
            with open(self.metrics_file, 'w') as f:
                json.dump(existing_metrics, f, indent=2)
                
            logger.info("Metrics saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    def push_to_prometheus(self):
        """Push metrics to Prometheus Pushgateway."""
        try:
            push_to_gateway(
                'localhost:9091',
                job='umbrella_metrics',
                registry=self.registry
            )
            logger.info("Metrics pushed to Prometheus")
        except Exception as e:
            logger.error(f"Failed to push metrics to Prometheus: {str(e)}")

def main():
    """Main execution function."""
    collector = MetricsCollector()
    
    while True:
        try:
            # Collect metrics
            metrics = collector.collect_all_metrics()
            
            # Save metrics to file
            collector.save_metrics(metrics)
            
            # Push to Prometheus if available
            collector.push_to_prometheus()
            
            # Wait for next collection
            time.sleep(60)  # Collect metrics every minute
            
        except KeyboardInterrupt:
            logger.info("Metrics collection stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in metrics collection: {str(e)}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    main() 
import sys
import logging
from datetime import datetime
from typing import Dict, Any
import json
import asyncio
from src.notifier import Notifier
from src.config.settings import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class WorkerEventListener:
    def __init__(self):
        self.notifier = Notifier()
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with loguru."""
        logger.add(
            str(settings.LOG_DIR / "event_listener_{time}.log"),
            rotation=settings.LOG_ROTATION_SIZE,
            retention=f"{settings.LOG_RETENTION_DAYS} days",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

    async def handle_event(self, headers: Dict[str, Any], payload: Dict[str, Any]):
        """Handle supervisor events."""
        try:
            event_type = headers.get('eventname')
            process_name = payload.get('processname')
            group_name = payload.get('groupname')
            from_state = payload.get('from_state')
            expected = payload.get('expected')
            pid = payload.get('pid')

            event_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'process_name': process_name,
                'group_name': group_name,
                'from_state': from_state,
                'expected': expected,
                'pid': pid
            }

            # Log do evento
            logger.info(f"Received event: {json.dumps(event_data)}")

            # Envia alerta para eventos críticos
            if event_type in ['PROCESS_STATE_EXITED', 'PROCESS_STATE_FATAL']:
                await self.notifier.send_alert(
                    level="error",
                    message=f"Worker process {process_name} {event_type}",
                    details=event_data
                )

        except Exception as e:
            logger.error(f"Error handling event: {str(e)}")
            await self.notifier.send_alert(
                level="error",
                message="Error in event listener",
                details={'error': str(e)}
            )

async def main():
    """Main event listener loop."""
    listener = WorkerEventListener()
    
    while True:
        try:
            # Lê o cabeçalho do evento
            headers = {}
            while True:
                line = sys.stdin.readline().strip()
                if not line:
                    break
                key, value = line.split(':', 1)
                headers[key] = value.strip()

            # Lê o payload do evento
            payload = {}
            while True:
                line = sys.stdin.readline().strip()
                if not line:
                    break
                key, value = line.split(':', 1)
                payload[key] = value.strip()

            # Processa o evento
            await listener.handle_event(headers, payload)

            # Envia resposta para o Supervisor
            print("RESULT 2")
            print("OK")
            sys.stdout.flush()

        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print("RESULT 4")
            print("FAIL")
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main()) 
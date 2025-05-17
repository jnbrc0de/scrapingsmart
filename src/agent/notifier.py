from typing import Dict, Any, Optional
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from .config import settings

class Notifier:
    """Gerenciador de notificações do sistema."""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger("notifier")
        self.config = config
        self.enabled = config.get('enabled', True)
        self.channels = config.get('channels', {})
        
    def notify_success(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Envia notificação de sucesso."""
        try:
            if not self.enabled:
                return True
                
            # Prepara mensagem
            title = "✅ Sucesso"
            content = self._format_message(message, data)
            
            # Envia para canais configurados
            success = True
            
            if self.channels.get('email', {}).get('enabled'):
                success &= self._send_email(title, content)
                
            if self.channels.get('slack', {}).get('enabled'):
                success &= self._send_slack(title, content)
                
            if self.channels.get('telegram', {}).get('enabled'):
                success &= self._send_telegram(title, content)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação de sucesso: {str(e)}")
            return False
            
    def notify_error(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Envia notificação de erro."""
        try:
            if not self.enabled:
                return True
                
            # Prepara mensagem
            title = "❌ Erro"
            content = self._format_message(message, data)
            
            # Envia para canais configurados
            success = True
            
            if self.channels.get('email', {}).get('enabled'):
                success &= self._send_email(title, content)
                
            if self.channels.get('slack', {}).get('enabled'):
                success &= self._send_slack(title, content)
                
            if self.channels.get('telegram', {}).get('enabled'):
                success &= self._send_telegram(title, content)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação de erro: {str(e)}")
            return False
            
    def notify_warning(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Envia notificação de aviso."""
        try:
            if not self.enabled:
                return True
                
            # Prepara mensagem
            title = "⚠️ Aviso"
            content = self._format_message(message, data)
            
            # Envia para canais configurados
            success = True
            
            if self.channels.get('email', {}).get('enabled'):
                success &= self._send_email(title, content)
                
            if self.channels.get('slack', {}).get('enabled'):
                success &= self._send_slack(title, content)
                
            if self.channels.get('telegram', {}).get('enabled'):
                success &= self._send_telegram(title, content)
                
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar notificação de aviso: {str(e)}")
            return False
            
    def _format_message(self, message: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Formata mensagem com dados."""
        try:
            content = f"{message}\n\n"
            
            if data:
                content += "Detalhes:\n"
                for key, value in data.items():
                    content += f"- {key}: {value}\n"
                    
            content += f"\nTimestamp: {datetime.now().isoformat()}"
            return content
            
        except Exception as e:
            self.logger.error(f"Erro ao formatar mensagem: {str(e)}")
            return message
            
    def _send_email(self, title: str, content: str) -> bool:
        """Envia notificação por email."""
        try:
            email_config = self.channels['email']
            
            # Prepara email
            msg = MIMEMultipart()
            msg['From'] = email_config['from']
            msg['To'] = email_config['to']
            msg['Subject'] = f"[SmartScraping] {title}"
            
            msg.attach(MIMEText(content, 'plain'))
            
            # Envia email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['username'], email_config['password'])
                server.send_message(msg)
                
            self.logger.info("Notificação enviada por email")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar email: {str(e)}")
            return False
            
    def _send_slack(self, title: str, content: str) -> bool:
        """Envia notificação para Slack."""
        try:
            slack_config = self.channels['slack']
            
            # Prepara payload
            payload = {
                'channel': slack_config['channel'],
                'text': f"*{title}*\n{content}",
                'username': slack_config.get('username', 'SmartScraping'),
                'icon_emoji': slack_config.get('icon_emoji', ':robot_face:')
            }
            
            # Envia mensagem
            response = requests.post(
                slack_config['webhook_url'],
                json=payload
            )
            
            if response.status_code == 200:
                self.logger.info("Notificação enviada para Slack")
                return True
            else:
                self.logger.error(f"Erro ao enviar para Slack: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar para Slack: {str(e)}")
            return False
            
    def _send_telegram(self, title: str, content: str) -> bool:
        """Envia notificação para Telegram."""
        try:
            telegram_config = self.channels['telegram']
            
            # Prepara mensagem
            message = f"*{title}*\n{content}"
            
            # Envia mensagem
            response = requests.post(
                f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage",
                json={
                    'chat_id': telegram_config['chat_id'],
                    'text': message,
                    'parse_mode': 'Markdown'
                }
            )
            
            if response.status_code == 200:
                self.logger.info("Notificação enviada para Telegram")
                return True
            else:
                self.logger.error(f"Erro ao enviar para Telegram: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar para Telegram: {str(e)}")
            return False 
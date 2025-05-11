# Sistema de Anti-Detecção

## Visão Geral

O sistema de anti-detecção é responsável por evitar a identificação do scraper como bot, implementando técnicas avançadas de evasão e simulação de comportamento humano.

## Componentes

### 1. Browser Profile Manager
- Gerencia perfis de navegador
- Implementa fingerprinting dinâmico
- Controla atributos do navegador
- Gerencia plugins e extensões

### 2. Human Behavior Simulator
- Simula movimentos de mouse
- Implementa padrões de scroll
- Controla tempos de interação
- Gera eventos aleatórios

### 3. Proxy Manager
- Gerencia rotação de proxies
- Implementa fallback
- Controla rate limiting
- Valida proxies

## Técnicas de Anti-Detecção

### 1. Fingerprinting

#### WebGL
```javascript
// Spoofing de WebGL
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    return getParameter.apply(this, arguments);
};
```

#### Canvas
```javascript
// Noise no Canvas
const originalGetContext = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function(type, attributes) {
    const context = originalGetContext.call(this, type, attributes);
    if (type === '2d') {
        const originalFillText = context.fillText;
        context.fillText = function() {
            const args = Array.from(arguments);
            args[1] += Math.random() * 0.1;
            args[2] += Math.random() * 0.1;
            return originalFillText.apply(this, args);
        };
    }
    return context;
};
```

#### Audio
```javascript
// Fingerprint de áudio
const audioContext = new AudioContext();
const analyser = audioContext.createAnalyser();
analyser.fftSize = 2048;
const bufferLength = analyser.frequencyBinCount;
const dataArray = new Uint8Array(bufferLength);
analyser.getByteFrequencyData(dataArray);
```

### 2. Comportamento Humano

#### Mouse Movement
```python
def generate_mouse_movement(start, end, duration):
    points = []
    current = start
    steps = int(duration * 60)  # 60fps
    
    for i in range(steps):
        progress = i / steps
        # Curva de Bezier para movimento natural
        point = bezier_curve(
            start,
            control_point1,
            control_point2,
            end,
            progress
        )
        points.append(point)
    
    return points
```

#### Scrolling
```python
def simulate_scroll(page, target_y):
    current_y = 0
    while current_y < target_y:
        # Scroll suave com variação
        step = random.uniform(100, 200)
        current_y += step
        page.mouse.wheel(0, step)
        time.sleep(random.uniform(0.1, 0.3))
```

#### Timing
```python
def human_delay():
    # Distribuição normal para delays
    mean = 1.0
    std = 0.3
    delay = random.normalvariate(mean, std)
    return max(0.1, min(3.0, delay))
```

### 3. Headers e Request

#### Headers Dinâmicos
```python
def generate_headers(profile):
    return {
        'User-Agent': profile.user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': profile.language,
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1'
    }
```

#### Cookie Management
```python
def manage_cookies(context, domain):
    cookies = context.cookies()
    if not cookies:
        # Cookies iniciais
        context.add_cookies([
            {
                'name': 'session_id',
                'value': generate_session_id(),
                'domain': domain,
                'path': '/'
            }
        ])
    else:
        # Atualização de cookies
        update_cookies(context, domain)
```

## Perfis de Navegador

### 1. Desktop

#### Chrome Windows
```python
CHROME_WINDOWS = {
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'platform': 'Win32',
    'webgl_vendor': 'Google Inc. (NVIDIA)',
    'webgl_renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)',
    'languages': ['pt-BR', 'pt', 'en-US', 'en'],
    'screen': {
        'width': 1920,
        'height': 1080,
        'color_depth': 24
    }
}
```

#### Firefox macOS
```python
FIREFOX_MACOS = {
    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    'platform': 'MacIntel',
    'webgl_vendor': 'Apple GPU',
    'webgl_renderer': 'Apple M1 Pro',
    'languages': ['pt-BR', 'pt', 'en-US', 'en'],
    'screen': {
        'width': 2560,
        'height': 1600,
        'color_depth': 30
    }
}
```

### 2. Mobile

#### iPhone 13 Pro
```python
IPHONE_13_PRO = {
    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'platform': 'iPhone',
    'webgl_vendor': 'Apple GPU',
    'webgl_renderer': 'Apple A15 GPU',
    'languages': ['pt-BR', 'pt', 'en-US', 'en'],
    'screen': {
        'width': 1170,
        'height': 2532,
        'color_depth': 24,
        'pixel_ratio': 3
    }
}
```

#### Samsung Galaxy S21
```python
SAMSUNG_S21 = {
    'user_agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'platform': 'Linux aarch64',
    'webgl_vendor': 'Qualcomm',
    'webgl_renderer': 'Adreno (TM) 650',
    'languages': ['pt-BR', 'pt', 'en-US', 'en'],
    'screen': {
        'width': 1080,
        'height': 2400,
        'color_depth': 24,
        'pixel_ratio': 2.625
    }
}
```

## Rotação de Proxies

### 1. Seleção de Proxy
```python
def select_proxy(domain, strategy):
    proxies = get_available_proxies()
    scored_proxies = []
    
    for proxy in proxies:
        score = 0
        # Score baseado em performance
        score += proxy.success_rate * 0.4
        # Score baseado em localização
        score += get_location_score(proxy, domain) * 0.3
        # Score baseado em uso recente
        score += get_usage_score(proxy) * 0.3
        
        scored_proxies.append((proxy, score))
    
    return select_best_proxy(scored_proxies, strategy)
```

### 2. Validação
```python
def validate_proxy(proxy):
    try:
        response = requests.get(
            'https://api.ipify.org?format=json',
            proxies={'http': proxy.url, 'https': proxy.url},
            timeout=10
        )
        return response.status_code == 200
    except:
        return False
```

## Monitoramento e Ajustes

### 1. Métricas
- Taxa de detecção
- Tempo de resposta
- Taxa de sucesso
- Uso de recursos

### 2. Ajustes Automáticos
- Rotação de perfis
- Ajuste de delays
- Variação de headers
- Modificação de fingerprints

### 3. Alertas
- Detecção de captcha
- Bloqueio de IP
- Mudanças no fingerprint
- Anomalias de comportamento

## Próximos Passos

1. Implementar machine learning para detecção de padrões
2. Adicionar suporte a mais navegadores
3. Melhorar simulação de comportamento
4. Expandir técnicas de evasão
5. Implementar análise de risco 
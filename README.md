# Mão robótica controlada por câmera

Este projeto usa a câmera do computador para detectar uma mão e controlar
cinco servos conectados a um Arduino: um servo para o polegar, o indicador, o
médio, o anelar e o mínimo.

> **Recomendação:** use Python 3.12. O código também foi escrito pensando em
> Python 3.14, mas MediaPipe e pyFirmata podem ainda não oferecer suporte
> oficial completo para essa versão.

## 1. O que você precisa

- Arduino compatível com Firmata e cabo USB;
- cinco servos e a estrutura mecânica da mão;
- fonte externa adequada para os servos;
- computador com câmera;
- Python 3.12 instalado;
- os arquivos `main.py`, `servo_braco3d.py`, `testar-dedos.py` e
  `requirements.txt`.

## 2. Monte a parte elétrica com segurança

Cada servo possui três fios:

| Dedo | Pino de sinal no Arduino |
| --- | ---: |
| Polegar | 3 |
| Indicador | 5 |
| Médio | 6 |
| Anelar | 9 |
| Mínimo | 10 |

Os números acima são apenas a configuração inicial. O fio de sinal de cada
servo vai ao respectivo pino. **Não alimente os cinco servos pelo pino 5 V do
Arduino**: use uma fonte externa dimensionada para a corrente dos motores e
conecte o GND da fonte ao GND do Arduino. Verifique a polaridade antes de
ligar. Um servo travado pode consumir muita corrente e danificar a placa ou a
fonte.

Se sua fiação for diferente, altere o dicionário `SERVO_PINS` em
`servo_braco3d.py` antes de executar os testes:

```python
SERVO_PINS = {
    "polegar": 3,
    "indicador": 5,
    "medio": 6,
    "anelar": 9,
    "minimo": 10,
}
```

## 3. Prepare o Arduino

1. Instale e abra a [Arduino IDE](https://www.arduino.cc/en/software).
2. Conecte o Arduino por USB.
3. Abra **Arquivo > Exemplos > Firmata > StandardFirmata**.
4. Em **Ferramentas > Placa**, escolha o modelo correto.
5. Em **Ferramentas > Porta**, escolha a porta do Arduino.
6. Clique em **Carregar**.

Anote a porta usada, por exemplo `COM3` no Windows ou `/dev/ttyACM0` no
Linux. Feche o Serial Monitor antes de executar o Python, pois ele pode
bloquear a porta.

## 4. Instale as bibliotecas Python

Abra um terminal na pasta do projeto e crie um ambiente virtual:

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação, execute o terminal como usuário com
permissão adequada ou use diretamente:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux/macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confira a instalação:

```bash
python -m py_compile main.py servo_braco3d.py testar-dedos.py
```

## 5. Teste os cinco dedos sem câmera

Com a fonte dos servos desligada, confira novamente a fiação. Depois ligue a
fonte externa e execute, substituindo `COM3` pela porta correta:

```bash
python testar-dedos.py --port COM3
```

O programa fecha e abre um dedo por vez. Se algum servo forçar a estrutura,
desligue imediatamente e ajuste seus limites em `servo_braco3d.py`:

```python
DEFAULT_SERVO_CONFIG = {
    "polegar": ServoConfig(pin=3, closed_angle=30, open_angle=130),
    # ajuste os demais dedos conforme a sua montagem
}
```

Os limites padrão são `20` graus fechado e `160` graus aberto. Eles são apenas
um ponto de partida: cada mecanismo precisa de calibração própria.

## 6. Execute com a câmera

### Teste primeiro sem Arduino

Este comando confirma que a câmera e o MediaPipe estão funcionando sem enviar
movimentos aos servos:

```bash
python main.py --camera 0 --no-arduino
```

Uma janela será aberta. Mostre a mão para a câmera e pressione `Q` ou `Esc`
para sair. Se houver mais de uma câmera, tente `--camera 1` ou outro índice.

### Controle a mão robótica

Com o Arduino conectado, o StandardFirmata carregado e a fonte dos servos
ligada:

```bash
python main.py --port COM3 --camera 0
```

O programa calcula a abertura aproximada de cada dedo e envia um ângulo
independente para cada servo. Para encerrar, pressione `Q` ou `Esc`; o programa
fecha os dedos e encerra a conexão.

## 7. Bloqueio do gesto ofensivo

Quando o programa identifica o dedo médio e o polegar levantados com os outros
dedos recolhidos, ele considera o gesto bloqueado. Nesse caso:

1. os cinco servos recebem a posição fechada, em vez de copiar o gesto;
2. a câmera mostra a imagem `assets/alerta.jpg` e a mensagem
   **GESTO BLOQUEADO**;
3. quando o gesto deixa de ser detectado, o controle normal volta
   automaticamente.

O detector usa a abertura estimada dos dedos e possui uma margem para evitar
falsos positivos. Ele não é um classificador perfeito: iluminação, posição da
mão e oclusões podem afetar a detecção. A imagem pode ser trocada usando
`--alert-image caminho/para/imagem.jpg`.

## 8. Solução de problemas

**“pyFirmata não está instalado”**

Ative `.venv` e execute `python -m pip install -r requirements.txt`.

**“Não foi possível conectar ao Arduino”**

Confira a porta, o cabo USB, o StandardFirmata e se nenhum outro programa está
usando a porta. No Linux, talvez seja necessário permitir acesso a
`/dev/ttyACM0` ou `/dev/ttyUSB0`.

**“Não foi possível abrir a câmera”**

Feche outros programas que usam a câmera, confira as permissões e tente outro
índice com `--camera`.

**Servo tremendo, invertido ou forçando o dedo**

Desligue a fonte, confirme o GND comum, ajuste `closed_angle` e `open_angle` e
verifique se o servo está instalado na direção esperada. Não aumente os limites
sem observar a mecânica.

**Instalação falha no Python 3.14**

Crie o ambiente com Python 3.12 e repita a instalação. MediaPipe e pyFirmata
podem não ter wheel ou suporte oficial para Python 3.14.

## 9. Arquivos do projeto

- `main.py`: captura a câmera, usa MediaPipe Hands e envia as aberturas;
- `servo_braco3d.py`: define pinos, limites, conversão de abertura para ângulo
  e conexão pyFirmata;
- `testar-dedos.py`: testa os cinco servos individualmente;
- `requirements.txt`: lista as dependências Python.
- `assets/alerta.jpg`: imagem exibida quando o gesto é bloqueado.

## Referências oficiais

- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)
- [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python)
- [OpenCV para Python](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [Pillow](https://pillow.readthedocs.io/en/stable/installation.html)
- [protobuf](https://protobuf.dev/getting_started/pythontutorial/)
- [pyFirmata](https://pyfirmata.readthedocs.io/en/latest/)
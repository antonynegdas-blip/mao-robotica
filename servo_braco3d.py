"""Controle seguro e reutilizável dos cinco servos da mão robótica.

Configuração:
    Ajuste ``SERVO_PINS`` para a fiação real antes de conectar o Arduino.
    Os limites são deliberadamente conservadores e podem ser alterados por
    ``ServoConfig``. Não ligue servos pela alimentação de 5 V do Arduino.

Referência oficial:
    https://pyfirmata.readthedocs.io/en/latest/
    https://github.com/firmata/pyFirmata

pyFirmata é um projeto antigo e não declara suporte específico a Python 3.14.
O módulo só é importado quando uma conexão é solicitada, permitindo testar o
mapeamento sem Arduino.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

FINGER_NAMES: tuple[str, ...] = ("polegar", "indicador", "medio", "anelar", "minimo")
SERVO_PINS: dict[str, int] = {
    "polegar": 3,
    "indicador": 5,
    "medio": 6,
    "anelar": 9,
    "minimo": 10,
}


@dataclass(frozen=True)
class ServoConfig:
    """Pino e limites mecânicos de um dedo.

    ``closed_angle`` é o ângulo para o dedo fechado e ``open_angle`` para o
    dedo aberto. Cada montagem pode precisar de valores e até direção próprios.
    """

    pin: int
    closed_angle: int = 20
    open_angle: int = 160

    def __post_init__(self) -> None:
        if not 0 <= self.pin <= 20:
            raise ValueError("O pino do servo deve estar entre 0 e 20.")
        for name, angle in (
            ("closed_angle", self.closed_angle),
            ("open_angle", self.open_angle),
        ):
            if not 0 <= angle <= 180:
                raise ValueError(f"{name} deve estar entre 0 e 180 graus.")


DEFAULT_SERVO_CONFIG: dict[str, ServoConfig] = {
    name: ServoConfig(pin=pin) for name, pin in SERVO_PINS.items()
}


def clamp01(value: float) -> float:
    """Limita uma abertura normalizada ao intervalo seguro [0, 1]."""

    return max(0.0, min(1.0, float(value)))


def opening_to_angle(opening: float, config: ServoConfig) -> int:
    """Converte abertura [0, 1] em ângulo respeitando os limites configurados."""

    opening = clamp01(opening)
    angle = config.closed_angle + opening * (config.open_angle - config.closed_angle)
    return round(max(0, min(180, angle)))


class RobotHand:
    """Gerencia a placa pyFirmata e os comandos dos servos."""

    def __init__(
        self,
        port: str,
        configs: Mapping[str, ServoConfig] | None = None,
    ) -> None:
        self.port = port
        self.configs = dict(configs or DEFAULT_SERVO_CONFIG)
        missing = set(FINGER_NAMES) - self.configs.keys()
        if missing:
            raise ValueError(f"Configuração ausente para: {', '.join(sorted(missing))}")
        self._board = None
        self._servos: dict[str, object] = {}

    @property
    def connected(self) -> bool:
        return self._board is not None

    def connect(self) -> None:
        """Conecta ao Arduino e configura os pinos como servo."""

        if self.connected:
            return
        try:
            from pyfirmata import Arduino
        except ImportError as exc:
            raise RuntimeError(
                "pyFirmata não está instalado. Execute: python -m pip install -r requirements.txt"
            ) from exc
        try:
            board = Arduino(self.port)
            self._board = board
            self._servos = {
                name: board.get_pin(f"d:{config.pin}:s")
                for name, config in self.configs.items()
            }
        except Exception as exc:
            self._board = None
            self._servos.clear()
            raise RuntimeError(
                f"Não foi possível conectar ao Arduino em {self.port!r}. "
                "Confira a porta, o StandardFirmata e a fiação."
            ) from exc

    def set_openings(self, openings: Mapping[str, float]) -> dict[str, int]:
        """Aplica aberturas e retorna os ângulos; exige conexão explícita."""

        angles = {
            name: opening_to_angle(openings.get(name, 0.0), config)
            for name, config in self.configs.items()
        }
        if not self.connected:
            raise RuntimeError(
                "Arduino desconectado: chame connect() antes de enviar movimentos."
            )
        for name, angle in angles.items():
            self._servos[name].write(angle)  # type: ignore[union-attr]
        return angles

    def close(self) -> None:
        """Fecha a mão de forma segura e encerra a conexão."""

        if self.connected:
            self.set_openings({name: 0.0 for name in FINGER_NAMES})
            self._board.exit()  # type: ignore[union-attr]
            self._board = None
            self._servos.clear()


def format_openings(openings: Mapping[str, float]) -> str:
    """Formata o estado para logs e sobreposição de câmera."""

    return " ".join(f"{name[:3]}={clamp01(openings.get(name, 0)):.0%}" for name in FINGER_NAMES)


def validate_openings(openings: Sequence[float]) -> tuple[float, ...]:
    """Valida cinco aberturas para uso por scripts de teste."""

    if len(openings) != len(FINGER_NAMES):
        raise ValueError(f"Esperadas {len(FINGER_NAMES)} aberturas.")
    return tuple(clamp01(value) for value in openings)

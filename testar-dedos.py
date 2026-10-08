"""Teste manual de cada dedo, sem movimentos simultâneos inesperados.

Uso:
    python testar-dedos.py --port COM3

Faça upload do StandardFirmata no Arduino, confira os cinco pinos em
``servo_braco3d.py`` e use uma fonte externa adequada para os servos.
"""

from __future__ import annotations

import argparse
import time

from servo_braco3d import FINGER_NAMES, RobotHand


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Porta serial do Arduino, por exemplo COM3.")
    parser.add_argument("--pause", type=float, default=0.8, help="Pausa entre movimentos em segundos.")
    args = parser.parse_args()
    if args.pause < 0:
        parser.error("--pause não pode ser negativa.")

    robot = RobotHand(args.port)
    robot.connect()
    try:
        for finger in FINGER_NAMES:
            print(f"Testando {finger}: fechando...")
            robot.set_openings({finger: 0.0})
            time.sleep(args.pause)
            print(f"Testando {finger}: abrindo...")
            robot.set_openings({finger: 1.0})
            time.sleep(args.pause)
        print("Teste concluído; fechando todos os dedos.")
        robot.set_openings({name: 0.0 for name in FINGER_NAMES})
    finally:
        robot.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

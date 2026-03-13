"""Espelho câmera -> mão robótica Arduino.

Requisitos e referências oficiais:
    MediaPipe Hands: https://google.github.io/mediapipe/solutions/hands.html
    Hand Landmarker atual: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
    OpenCV Python: https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html
    Pillow: https://pillow.readthedocs.io/en/stable/installation.html
    protobuf: https://protobuf.dev/getting_started/pythontutorial/

Uso:
    python main.py --port COM3
    python main.py --camera 0 --no-arduino

Python 3.14: o interpretador é o alvo do projeto, mas MediaPipe e pyFirmata
podem ainda não publicar wheels/suporte oficial para 3.14. Consulte as fontes
acima e use Python 3.12/3.13 se a instalação falhar. ``mp.solutions.hands`` é
a API de MediaPipe Hands usada aqui; a API Tasks atual requer um modelo
``.task`` baixado separadamente e não é misturada silenciosamente neste script.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Mapping

from servo_braco3d import FINGER_NAMES, RobotHand, format_openings

try:
    import cv2
    import mediapipe as mp
except ImportError as exc:
    cv2 = None
    mp = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _distance(a: Any, b: Any) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _finger_open(landmarks: Any, tip: int, pip: int, mcp: int) -> float:
    """Estima abertura usando distância tip->MCP relativa a PIP->MCP."""

    baseline = _distance(landmarks[mcp], landmarks[pip])
    if baseline <= 1e-6:
        return 0.0
    extension = _distance(landmarks[mcp], landmarks[tip]) / baseline
    return max(0.0, min(1.0, (extension - 1.0) / 1.2))


def calculate_openings(landmarks: Any) -> dict[str, float]:
    """Converte os 21 landmarks normalizados em abertura dos cinco dedos."""

    # Índices oficiais dos landmarks: https://google.github.io/mediapipe/solutions/hands.html
    fingers = {
        "polegar": (4, 2, 1),
        "indicador": (8, 6, 5),
        "medio": (12, 10, 9),
        "anelar": (16, 14, 13),
        "minimo": (20, 18, 17),
    }
    return {
        name: _finger_open(landmarks, tip, pip, mcp)
        for name, (tip, pip, mcp) in fingers.items()
    }


def is_obscene_gesture(openings: Mapping[str, float]) -> bool:
    """Detecta dedo médio levantado com os outros dedos recolhidos.

    Os limiares deixam uma margem para pequenas oscilações da câmera. O gesto
    só é bloqueado quando o médio está claramente mais aberto que os demais.
    """

    return (
        openings.get("medio", 0.0) >= 0.72
        and openings.get("indicador", 0.0) <= 0.45
        and openings.get("anelar", 0.0) <= 0.45
        and openings.get("minimo", 0.0) <= 0.45
    )


def _require_dependencies() -> tuple[Any, Any]:
    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "Dependências de câmera ausentes. Execute: "
            "python -m pip install -r requirements.txt"
        ) from _IMPORT_ERROR
    return cv2, mp


def _load_alert_image(cv2_module: Any, image_path: Path) -> Any:
    alert = cv2_module.imread(str(image_path))
    if alert is None:
        raise RuntimeError(f"Não foi possível abrir a imagem de alerta: {image_path}")
    return alert


def _draw_alert(frame: Any, cv2_module: Any, alert_image: Any) -> None:
    height, width = frame.shape[:2]
    alert_width = min(280, width // 3)
    ratio = alert_width / alert_image.shape[1]
    alert = cv2_module.resize(
        alert_image, (alert_width, max(1, round(alert_image.shape[0] * ratio)))
    )
    frame[10 : 10 + alert.shape[0], width - alert.shape[1] - 10 : width - 10] = alert
    cv2_module.putText(
        frame,
        "GESTO BLOQUEADO",
        (10, height - 25),
        cv2_module.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )


def run(
    camera_index: int,
    robot: RobotHand | None,
    mirror: bool = True,
    alert_image_path: Path | None = None,
) -> None:
    """Executa captura até Q/Esc; Ctrl+C também encerra sem esconder erros."""

    cv2_module, mp_module = _require_dependencies()
    alert_image = None
    if alert_image_path is not None:
        alert_image = _load_alert_image(cv2_module, alert_image_path)
    capture = cv2_module.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(
            f"Não foi possível abrir a câmera {camera_index}. "
            "Confira permissões ou use --camera com outro índice."
        )
    try:
        with mp_module.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        ) as hands:
            while True:
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("A câmera não forneceu um quadro válido.")
                if mirror:
                    frame = cv2_module.flip(frame, 1)
                result = hands.process(cv2_module.cvtColor(frame, cv2_module.COLOR_BGR2RGB))
                if result.multi_hand_landmarks:
                    openings = calculate_openings(result.multi_hand_landmarks[0].landmark)
                    blocked = is_obscene_gesture(openings)
                    if blocked and robot is not None:
                        robot.set_openings({name: 0.0 for name in FINGER_NAMES})
                    elif robot is not None:
                        robot.set_openings(openings)
                    if blocked:
                        if alert_image is not None:
                            _draw_alert(frame, cv2_module, alert_image)
                        else:
                            cv2_module.putText(
                                frame, "GESTO BLOQUEADO", (10, 30),
                                cv2_module.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2
                            )
                    else:
                        cv2_module.putText(
                            frame,
                            format_openings(openings),
                            (10, 30),
                            cv2_module.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                else:
                    cv2_module.putText(
                        frame, "Nenhuma mao detectada", (10, 30),
                        cv2_module.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2
                    )
                cv2_module.imshow("Mao robotica - Q/Esc encerra", frame)
                if cv2_module.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
    finally:
        capture.release()
        cv2_module.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Porta serial do Arduino, por exemplo COM3.")
    parser.add_argument("--camera", type=int, default=0, help="Índice da câmera (padrão: 0).")
    parser.add_argument("--no-arduino", action="store_true", help="Mostra a detecção sem enviar servos.")
    parser.add_argument("--no-mirror", action="store_true", help="Não espelha a imagem.")
    parser.add_argument(
        "--alert-image",
        type=Path,
        default=Path(__file__).parent / "assets" / "alerta.jpg",
        help="Imagem exibida quando o gesto bloqueado é detectado.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    robot = None
    try:
        if not args.no_arduino:
            if not args.port:
                raise RuntimeError(
                    "Informe --port (ex.: COM3) ou use --no-arduino para executar sem Arduino."
                )
            robot = RobotHand(args.port)
            robot.connect()
        run(
            args.camera,
            robot,
            mirror=not args.no_mirror,
            alert_image_path=args.alert_image,
        )
    except KeyboardInterrupt:
        return 0
    finally:
        if robot is not None:
            robot.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)

"""This module contains the main process of the robot."""

import subprocess
import time
import pyautogui

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueElement


# pylint: disable-next=unused-argument
def process(orchestrator_connection: OrchestratorConnection, queue_element: QueueElement | None = None) -> None:
    """Do the primary process of the robot."""
    print("HEY!!!!!")
    orchestrator_connection.log_trace("Running process.")

    subprocess.Popen(["notepad.exe"])
    time.sleep(3)
    
    pyautogui.write("Hello World", interval=0.2)
